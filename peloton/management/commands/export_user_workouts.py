"""
Management command to export a user's workouts to a JSON file with simplified fields.

Exports entries with: datestamp (`created_at`), class title (`title`), type (`type`), and workout id (`workout_id`).

Supports an interactive `--sso` flow to obtain a bearer token for debugging.

Usage examples:
  python manage.py export_user_workouts --connection-id 2 --output-dir jsons
  python manage.py export_user_workouts --username roo@haresign.dev --sso
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings

from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient, PelotonAPIError, AUTH_REDIRECT_URI

User = get_user_model()


class Command(BaseCommand):
    help = 'Export simplified user workouts to a JSON file (created_at, title, type, workout_id)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--connection-id',
            type=int,
            default=2,
            help='PelotonConnection id to use (default: 2)'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Django username/email to select Peloton connection (alternative to --connection-id)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Maximum number of workouts to export (0 = all)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='jsons',
            help='Directory under project BASE_DIR to save output JSON (default: jsons)'
        )
        parser.add_argument(
            '--sso',
            action='store_true',
            help='Run interactive SSO flow to get a bearer token for debugging'
        )

    def handle(self, *args, **options):
        connection_id = options.get('connection_id')
        username = options.get('username')
        limit = options.get('limit', 0) or 0
        output_dir = options.get('output_dir', 'jsons')
        do_sso = options.get('sso', False)

        # Locate connection
        connection = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User with username "{username}" not found')
            try:
                connection = PelotonConnection.objects.get(user=user, is_active=True)
            except PelotonConnection.DoesNotExist:
                raise CommandError(f'No active PelotonConnection for user "{username}"')
        else:
            try:
                connection = PelotonConnection.objects.get(pk=connection_id)
            except PelotonConnection.DoesNotExist:
                raise CommandError(f'PelotonConnection with id {connection_id} not found')

        self.stdout.write(self.style.SUCCESS(f'Using PelotonConnection id={connection.pk} user={connection.user.email}'))

        # If user requested SSO interactive flow, run it now
        if do_sso:
            # Create an unauthenticated client to generate auth URL
            client = PelotonClient()
            auth_url, code_verifier = client.get_authorization_url(AUTH_REDIRECT_URI)
            self.stdout.write('\nInteractive SSO flow:')
            self.stdout.write('  1) Open this URL in a browser and complete login:')
            self.stdout.write(f'     {auth_url}')
            self.stdout.write('  2) After login you will be redirected to a URL containing a `code` query parameter.')
            self.stdout.write('  3) Paste the `code` value here (the command will exchange it for a token).')
            code = input('\nPaste authorization code (or press Enter to skip): ').strip()
            if code:
                try:
                    token = client.exchange_code_for_token(code, code_verifier, AUTH_REDIRECT_URI)
                    # Save token to connection (bearer + refresh + expiry)
                    connection.bearer_token = token.access_token
                    if token.refresh_token:
                        connection.refresh_token = token.refresh_token
                    connection.token_expires_at = datetime.utcnow() + timedelta(seconds=token.expires_in or 0)
                    connection.save()
                    self.stdout.write(self.style.SUCCESS('  ✓ Saved bearer/refresh token to connection'))
                except PelotonAPIError as e:
                    raise CommandError(f'SSO token exchange failed: {e}')
            else:
                self.stdout.write(self.style.WARNING('SSO code not provided; continuing with existing credentials'))

        # Obtain client from connection
        try:
            client = connection.get_client()
        except Exception as e:
            raise CommandError(f'Failed to get Peloton client from connection: {e}')

        # Create output directory under BASE_DIR
        base = Path(settings.BASE_DIR)
        out_dir = base / output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # Output filename
        safe_name = f'peloton_connection_{connection.pk}_workouts.json'
        out_file = out_dir / safe_name

        self.stdout.write(f'Fetching workouts and writing to: {out_file}')

        exported = []
        count = 0

        # Need a user id for the API
        user_id = connection.peloton_user_id
        if not user_id:
            # Try to fetch current user via client and set peloton_user_id
            try:
                me = client.fetch_current_user()
                user_id = me.get('id')
                if user_id:
                    connection.peloton_user_id = str(user_id)
                    connection.save()
            except Exception:
                pass

        if not user_id:
            raise CommandError('No Peloton user id available on connection (and fetch failed).')

        try:
            iterator = client.iter_user_workouts(user_id, limit=50)
            for workout in iterator:
                # Extract fields robustly
                workout_id = workout.get('id') or workout.get('workout_id')
                created_at = workout.get('created_at') or workout.get('created') or workout.get('created_at_ms')
                # If created_at is milliseconds timestamp, convert to iso
                if isinstance(created_at, (int, float)):
                    # assume milliseconds
                    try:
                        created_at_iso = datetime.utcfromtimestamp(created_at / 1000.0).isoformat() + 'Z'
                    except Exception:
                        created_at_iso = str(created_at)
                else:
                    created_at_iso = created_at

                ride = workout.get('ride') or {}
                title = ride.get('title') or ride.get('name') or workout.get('title') or workout.get('class_title') or 'Unknown'
                wtype = ride.get('fitness_discipline') or workout.get('fitness_discipline') or ride.get('type') or workout.get('type') or 'Unknown'

                exported.append({
                    'created_at': created_at_iso,
                    'title': title,
                    'type': wtype,
                    'workout_id': workout_id,
                })

                count += 1
                if limit and count >= limit:
                    break

        except PelotonAPIError as e:
            raise CommandError(f'Peloton API error while fetching workouts: {e}')
        except Exception as e:
            raise CommandError(f'Error while fetching workouts: {e}')

        # Save to file
        with open(out_file, 'w') as f:
            json.dump(exported, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'✓ Exported {len(exported)} workouts to {out_file}'))
