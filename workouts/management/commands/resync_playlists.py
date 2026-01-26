"""
Management command to resync playlists for existing RideDetail objects.

This fetches playlists from the Peloton API for classes that are already in the database.
Useful for populating playlists for classes that were synced before the playlist feature was added.

Usage:
    python manage.py resync_playlists
    python manage.py resync_playlists --update-existing
    python manage.py resync_playlists --limit 10
    python manage.py resync_playlists --ride-id <peloton_ride_id>
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from peloton.models import PelotonConnection
from workouts.models import RideDetail, Playlist

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Resync playlists for existing RideDetail objects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing playlists (by default, only creates new ones)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of playlists to fetch (for testing)'
        )
        parser.add_argument(
            '--ride-id',
            type=str,
            default=None,
            help='Resync playlist for a specific ride ID only'
        )
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Use specific user\'s Peloton connection (by Peloton leaderboard name)'
        )

    def handle(self, *args, **options):
        update_existing = options['update_existing']
        limit = options.get('limit')
        ride_id = options.get('ride_id')
        username = options.get('username')
        
        # Get authenticated client
        try:
            if username:
                # Find user by Peloton leaderboard name
                from accounts.models import Profile
                try:
                    profile = Profile.objects.get(peloton_leaderboard_name=username)
                    user = profile.user
                except Profile.DoesNotExist:
                    raise CommandError(f'User with Peloton leaderboard name "{username}" not found')
                
                connection = PelotonConnection.objects.get(user=user)
            else:
                # Use first available connection
                connection = PelotonConnection.objects.select_related('user').first()
                if not connection:
                    raise CommandError('No Peloton connection found. Please connect a Peloton account first.')
        except PelotonConnection.DoesNotExist:
            raise CommandError('No Peloton connection found. Please connect a Peloton account first.')
        
        client = connection.get_client()
        if not client:
            raise CommandError('Failed to get authenticated Peloton client')
        
        self.stdout.write(self.style.SUCCESS(f'Using connection for user: {connection.user.email}'))
        self.stdout.write('')
        
        # Get RideDetail queryset
        if ride_id:
            ride_details = RideDetail.objects.filter(peloton_ride_id=ride_id)
            if not ride_details.exists():
                raise CommandError(f'RideDetail with peloton_ride_id "{ride_id}" not found')
        else:
            # Get all RideDetails, optionally filtering by whether they have playlists
            if update_existing:
                # Include all RideDetails (will update existing playlists)
                ride_details = RideDetail.objects.all()
            else:
                # Only get RideDetails without playlists
                ride_details = RideDetail.objects.filter(playlist__isnull=True)
        
        total_count = ride_details.count()
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No RideDetails found to process.'))
            return
        
        self.stdout.write(f'Found {total_count} RideDetail{"s" if total_count != 1 else ""} to process')
        if not update_existing:
            self.stdout.write('  (Only processing RideDetails without playlists)')
        self.stdout.write('')
        
        # Process playlists
        playlists_created = 0
        playlists_updated = 0
        playlists_skipped = 0
        playlists_failed = 0
        processed = 0
        
        try:
            with transaction.atomic():
                for ride_detail in ride_details.select_related('workout_type', 'instructor'):
                    processed += 1
                    
                    if limit and processed > limit:
                        self.stdout.write(self.style.WARNING(f'Reached limit of {limit} playlists'))
                        break
                    
                    # Check if playlist already exists
                    try:
                        existing_playlist = ride_detail.playlist
                        if not update_existing:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  [{processed}/{total_count}] Skipping {ride_detail.title} (playlist already exists)'
                                )
                            )
                            playlists_skipped += 1
                            continue
                    except Playlist.DoesNotExist:
                        existing_playlist = None
                    
                    # Fetch playlist from ride details (playlist is included in ride_details response)
                    self.stdout.write(f'  [{processed}/{total_count}] Fetching ride details for: {ride_detail.title}')
                    try:
                        ride_details = client.fetch_ride_details(ride_detail.peloton_ride_id)
                        playlist_data = ride_details.get('playlist')
                        if not playlist_data:
                            # No playlist in ride details (shouldn't happen for most classes, but possible)
                            self.stdout.write(
                                self.style.WARNING(f'    No playlist in ride details')
                            )
                            playlists_skipped += 1
                            continue
                    except Exception as e:
                        # For other errors (network issues, auth failures, etc.), treat as failure
                        playlists_failed += 1
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ Failed to fetch ride details: {e}')
                        )
                        logger.exception(f'Error fetching ride details for ride_id {ride_detail.peloton_ride_id}')
                        continue
                    
                    try:
                        # Extract playlist information
                        peloton_playlist_id = playlist_data.get('id')
                        songs = playlist_data.get('songs', [])
                        top_artists = playlist_data.get('top_artists', [])
                        top_albums = playlist_data.get('top_albums', [])
                        stream_id = playlist_data.get('stream_id')
                        stream_url = playlist_data.get('stream_url')
                        
                        # Create or update playlist
                        playlist, created = Playlist.objects.update_or_create(
                            ride_detail=ride_detail,
                            defaults={
                                'peloton_playlist_id': peloton_playlist_id,
                                'songs': songs,
                                'top_artists': top_artists,
                                'top_albums': top_albums,
                                'stream_id': stream_id,
                                'stream_url': stream_url,
                                'is_top_artists_shown': playlist_data.get('is_top_artists_shown', False),
                                'is_playlist_shown': playlist_data.get('is_playlist_shown', False),
                                'is_in_class_music_shown': playlist_data.get('is_in_class_music_shown', False),
                            }
                        )
                        
                        if created:
                            playlists_created += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'    ✓ Created playlist with {len(songs)} songs')
                            )
                        else:
                            playlists_updated += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'    ↻ Updated playlist with {len(songs)} songs')
                            )
                    
                    except Exception as e:
                        # This should not happen if we handled the fetch_playlist error above,
                        # but catch any errors during save/update
                        playlists_failed += 1
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ Failed to save playlist: {e}')
                        )
                        logger.exception(f'Error saving playlist for ride_id {ride_detail.peloton_ride_id}')
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nInterrupted by user'))
            raise CommandError('Command interrupted')
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Created: {playlists_created}')
        if update_existing:
            self.stdout.write(f'  Updated: {playlists_updated}')
        self.stdout.write(f'  Skipped: {playlists_skipped}')
        self.stdout.write(f'  Failed: {playlists_failed}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
