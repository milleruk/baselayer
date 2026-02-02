"""
Management command to sync Peloton class library (archived rides) into the app.

This command fetches all archived classes from Peloton's API and stores them in the RideDetail model.
It supports filtering by fitness discipline (cycling, running, etc.) and year.

Usage:
    python manage.py sync_class_library
    python manage.py sync_class_library --disciplines cycling,running --year 2025
    python manage.py sync_class_library --disciplines cycling --limit 100 --dry-run
"""

import logging
import time
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonAPIError
from workouts.tasks import store_ride_detail_from_api

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Peloton class library (archived rides) into the app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--disciplines',
            type=str,
            default='cycling,running',
            help='Comma-separated list of fitness disciplines to sync (default: cycling,running)'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Filter by year (e.g., 2025). If not specified, syncs all available classes.'
        )
        parser.add_argument(
            '--month',
            type=int,
            default=None,
            help='Filter by month (1-12). Must be used with --year. If not specified, syncs entire year.'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of classes to sync (for testing). If not specified, syncs all available.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Use specific user\'s Peloton connection (by Peloton leaderboard name)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay in seconds between API calls to avoid rate limiting (default: 0.5)'
        )

    def handle(self, *args, **options):
        disciplines_str = options.get('disciplines', 'cycling,running')
        year = options.get('year')
        month = options.get('month')
        limit = options.get('limit')
        dry_run = options.get('dry_run', False)
        username = options.get('username')
        delay = options.get('delay', 0.5)
        
        # Validate month if provided
        if month is not None:
            if year is None:
                raise CommandError('--month requires --year to be specified')
            if not (1 <= month <= 12):
                raise CommandError('--month must be between 1 and 12')
        
        # Parse disciplines
        disciplines = [d.strip().lower() for d in disciplines_str.split(',') if d.strip()]
        if not disciplines:
            raise CommandError('At least one discipline must be specified')
        
        # Get authenticated client
        try:
            if username:
                from accounts.models import Profile
                try:
                    profile = Profile.objects.get(peloton_leaderboard_name=username)
                    user = profile.user
                except Profile.DoesNotExist:
                    raise CommandError(f'User with Peloton leaderboard name "{username}" not found')
                
                connection = PelotonConnection.objects.get(user=user, is_active=True)
            else:
                connection = PelotonConnection.objects.select_related('user').filter(is_active=True).first()
                if not connection:
                    raise CommandError('No active Peloton connection found. Please connect a Peloton account first.')
        except PelotonConnection.DoesNotExist:
            raise CommandError('No active Peloton connection found. Please connect a Peloton account first.')
        
        client = connection.get_client()
        if not client:
            raise CommandError('Failed to get authenticated Peloton client')
        
        self.stdout.write(self.style.SUCCESS(f'Using connection for user: {connection.user.email}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        self.stdout.write('')
        
        # Calculate date range if year is specified
        start_date = None
        end_date = None
        if year:
            if month:
                # Filter by specific month
                # Calculate last day of month
                if month == 12:
                    last_day = 31
                    next_month = 1
                    next_year = year + 1
                else:
                    from calendar import monthrange
                    last_day = monthrange(year, month)[1]
                    next_month = month + 1
                    next_year = year
                
                # Use seconds for timestamps (Peloton API may expect seconds, not milliseconds)
                start_date = int(datetime(year, month, 1, 0, 0, 0).timestamp())
                # End date is start of next month (exclusive) minus 1 second
                end_date = int(datetime(next_year, next_month, 1, 0, 0, 0).timestamp()) - 1
                month_name = datetime(year, month, 1).strftime('%B')
                self.stdout.write(f'Filtering by {month_name} {year}: {datetime.fromtimestamp(start_date).date()} to {datetime.fromtimestamp(end_date).date()}')
                # Also try milliseconds for API (some endpoints expect milliseconds)
                start_date_ms = start_date * 1000
                end_date_ms = end_date * 1000
                start_date = start_date_ms  # Use milliseconds for API
                end_date = end_date_ms
            else:
                # Filter by entire year
                # Use seconds for timestamps
                start_date_sec = int(datetime(year, 1, 1, 0, 0, 0).timestamp())
                end_date_sec = int(datetime(year, 12, 31, 23, 59, 59).timestamp())
                self.stdout.write(f'Filtering by year {year}: {datetime.fromtimestamp(start_date_sec).date()} to {datetime.fromtimestamp(end_date_sec).date()}')
                # Convert to milliseconds for API
                start_date = start_date_sec * 1000
                end_date = end_date_sec * 1000
        
        # Statistics
        stats = {
            'total_fetched': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'by_discipline': {}
        }
        
        # Process each discipline
        for discipline in disciplines:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Processing {discipline.upper()} classes...'))
            self.stdout.write('=' * 60)
            
            discipline_stats = {
                'fetched': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': 0
            }
            
            try:
                # Fetch archived rides for this discipline
                # Note: Peloton API uses 'running' for running/treadmill classes
                # IMPORTANT: The API date filtering doesn't work reliably - it ignores date params
                # So we fetch without date filters and do all filtering client-side
                # The API returns classes in reverse chronological order (newest first),
                # so we may need to paginate through many pages to find older classes
                # When filtering by date, we'll keep fetching until we reach the start date
                if start_date or end_date:
                    self.stdout.write(self.style.WARNING(f'  Note: API date filters are ignored. Fetching all classes and filtering client-side.'))
                    self.stdout.write(self.style.WARNING(f'  This may take a while as we paginate through recent classes to reach the target date range.'))
                
                ride_iterator = client.iter_archived_rides(
                    limit=50,  # Fetch 50 at a time
                    fitness_discipline=discipline,
                    start_date=None,  # Don't pass date filters - API ignores them
                    end_date=None,    # Don't pass date filters - API ignores them
                    max_pages=None  # Fetch all pages until we find the date range (or hit limit)
                )
                
                processed_count = 0
                skipped_by_date = 0
                total_from_api = 0
                for ride in ride_iterator:
                    total_from_api += 1
                    # Check limit
                    if limit and processed_count >= limit:
                        break
                    
                    # Get title early for debugging
                    title = ride.get('title', 'Unknown')
                    
                    # Client-side date filtering (API date filters don't work - API ignores them)
                    # The archived endpoint returns rides with 'original_air_time' field (in seconds)
                    # API returns classes in reverse chronological order (newest first)
                    if start_date or end_date:
                        ride_air_time = ride.get('original_air_time') or ride.get('scheduled_start_time') or ride.get('created_at')
                        if ride_air_time:
                            # Convert ride timestamp to seconds (API returns in seconds)
                            ride_timestamp_sec = ride_air_time / 1000 if ride_air_time >= 1e12 else ride_air_time
                            # Convert our date filters from milliseconds to seconds for comparison
                            start_timestamp_sec = (start_date / 1000) if start_date >= 1e12 else start_date
                            end_timestamp_sec = (end_date / 1000) if end_date >= 1e12 else end_date
                            
                            # Skip if outside date range
                            if start_date and ride_timestamp_sec < start_timestamp_sec:
                                skipped_by_date += 1
                                if dry_run and skipped_by_date <= 3:  # Show first few skipped for debugging
                                    ride_date = datetime.fromtimestamp(ride_timestamp_sec).strftime('%Y-%m-%d')
                                    self.stdout.write(self.style.WARNING(f'  Skipped (before range): {title[:50]} - {ride_date}'))
                                continue
                            if end_date and ride_timestamp_sec > end_timestamp_sec:
                                skipped_by_date += 1
                                if dry_run and skipped_by_date <= 3:  # Show first few skipped for debugging
                                    ride_date = datetime.fromtimestamp(ride_timestamp_sec).strftime('%Y-%m-%d')
                                    self.stdout.write(self.style.WARNING(f'  Skipped (after range): {title[:50]} - {ride_date}'))
                                continue
                        elif start_date or end_date:
                            # If we have date filters but ride has no timestamp, skip it
                            skipped_by_date += 1
                            if dry_run and skipped_by_date <= 3:  # Show first few skipped for debugging
                                self.stdout.write(self.style.WARNING(f'  Skipped (no timestamp): {title[:50]}'))
                            continue
                        
                        # If we're filtering by date and we've gone before the start date,
                        # we can stop fetching since API returns in reverse chronological order
                        # (newest first, so if we're before start_date, all remaining will be even older)
                        if start_date and ride_air_time:
                            ride_timestamp_sec = ride_air_time / 1000 if ride_air_time >= 1e12 else ride_air_time
                            start_timestamp_sec = (start_date / 1000) if start_date >= 1e12 else start_date
                            if ride_timestamp_sec < start_timestamp_sec:
                                # We've gone before our start date - all remaining rides will be even older
                                # Note: This assumes API returns in reverse chronological order (newest first)
                                if dry_run:
                                    ride_date = datetime.fromtimestamp(ride_timestamp_sec).strftime('%Y-%m-%d')
                                    self.stdout.write(self.style.WARNING(f'  Stopped fetching - reached start of date range (last ride: {ride_date})'))
                                break
                    
                    stats['total_fetched'] += 1
                    discipline_stats['fetched'] += 1
                    processed_count += 1
                    
                    # Extract ride ID
                    ride_id = ride.get('id') or ride.get('ride_id')
                    if not ride_id:
                        self.stdout.write(self.style.WARNING(f'  Skipping ride without ID: {ride}'))
                        discipline_stats['skipped'] += 1
                        stats['skipped'] += 1
                        continue
                    
                    ride_id = str(ride_id)
                    
                    # Check if already exists - skip early to avoid unnecessary processing
                    from workouts.models import RideDetail
                    if RideDetail.objects.filter(peloton_ride_id=ride_id).exists():
                        discipline_stats['skipped'] += 1
                        stats['skipped'] += 1
                        continue
                    
                    # Debug: Log first few rides for each discipline
                    if processed_count <= 3 and dry_run:
                        ride_air_time_debug = ride.get('original_air_time')
                        if ride_air_time_debug:
                            ride_timestamp_sec_debug = ride_air_time_debug / 1000 if ride_air_time_debug >= 1e12 else ride_air_time_debug
                            ride_date_debug = datetime.fromtimestamp(ride_timestamp_sec_debug).strftime('%Y-%m-%d')
                            self.stdout.write(f'  Sample ride: {title[:50]} - Date: {ride_date_debug}, Discipline: {ride.get("fitness_discipline")}')
                    
                    # Skip warm up and cool down rides
                    title_lower = title.lower()
                    if any(keyword in title_lower for keyword in ['warm up', 'warmup', 'cool down', 'cooldown']):
                        discipline_stats['skipped'] += 1
                        stats['skipped'] += 1
                        continue
                    
                    # For cycling classes, only sync Power Zone classes (timer only works for PZ)
                    if discipline == 'cycling':
                        is_power_zone = False
                        
                        # Check is_power_zone_class flag
                        if ride.get('is_power_zone_class') or ride.get('is_power_zone'):
                            is_power_zone = True
                        
                        # Check title for Power Zone keywords
                        if not is_power_zone:
                            if 'power zone' in title_lower or ' pz ' in title_lower or title_lower.startswith('pz ') or title_lower.endswith(' pz'):
                                is_power_zone = True
                        
                        # Check class_type_ids for Power Zone class type
                        if not is_power_zone:
                            class_type_ids = ride.get('class_type_ids', [])
                            if isinstance(class_type_ids, list):
                                # Power Zone class type IDs (these may vary, but common ones are checked)
                                # You may need to adjust these based on actual Peloton class type IDs
                                pz_keywords = ['power_zone', 'powerzone', 'pz']
                                for class_type_id in class_type_ids:
                                    if isinstance(class_type_id, str) and any(kw in class_type_id.lower() for kw in pz_keywords):
                                        is_power_zone = True
                                        break
                        
                        # Skip non-Power Zone cycling classes
                        if not is_power_zone:
                            discipline_stats['skipped'] += 1
                            stats['skipped'] += 1
                            continue
                    
                    # Ride passed all filters - will be processed
                    if dry_run:
                        self.stdout.write(f'  Would create: {title} (ID: {ride_id})')
                        discipline_stats['created'] += 1
                        continue
                    
                    # Fetch and store ride details
                    try:
                        result = store_ride_detail_from_api(client, ride_id, logger)
                        
                        if result['status'] == 'success':
                            if result.get('created'):
                                discipline_stats['created'] += 1
                                stats['created'] += 1
                                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {title}'))
                            else:
                                discipline_stats['updated'] += 1
                                stats['updated'] += 1
                                self.stdout.write(f'  ↻ Updated: {title}')
                        else:
                            discipline_stats['errors'] += 1
                            stats['errors'] += 1
                            self.stdout.write(self.style.ERROR(f'  ✗ Error: {title} - {result.get("message", "Unknown error")}'))
                        
                        # Rate limiting delay
                        if delay > 0:
                            time.sleep(delay)
                    
                    except Exception as e:
                        discipline_stats['errors'] += 1
                        stats['errors'] += 1
                        self.stdout.write(self.style.ERROR(f'  ✗ Exception: {title} - {str(e)}'))
                        logger.exception(f'Error processing ride {ride_id}')
                    
                    # Progress indicator
                    if processed_count % 10 == 0:
                        self.stdout.write(f'  Processed {processed_count} rides...')
                
                stats['by_discipline'][discipline] = discipline_stats
                self.stdout.write('')
                self.stdout.write(f'  {discipline.upper()} Summary:')
                self.stdout.write(f'    Total from API: {total_from_api}')
                self.stdout.write(f'    Processed: {discipline_stats["fetched"]}')
                if skipped_by_date > 0:
                    self.stdout.write(f'    Skipped (outside date range): {skipped_by_date}')
                if not dry_run:
                    self.stdout.write(f'    Created: {discipline_stats["created"]}')
                    self.stdout.write(f'    Updated: {discipline_stats["updated"]}')
                self.stdout.write(f'    Skipped: {discipline_stats["skipped"]}')
                self.stdout.write(f'    Errors: {discipline_stats["errors"]}')
                
                # Debug: Show why rides might have been skipped
                if total_from_api > 0 and discipline_stats["fetched"] == 0:
                    self.stdout.write(self.style.WARNING(f'    ⚠ Warning: API returned {total_from_api} rides but none were processed. Check date filtering and other filters.'))
            
            except PelotonAPIError as e:
                self.stdout.write(self.style.ERROR(f'API error fetching {discipline} rides: {e}'))
                stats['errors'] += 1
                logger.exception(f'API error fetching {discipline} rides')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing {discipline} rides: {e}'))
                stats['errors'] += 1
                logger.exception(f'Error processing {discipline} rides')
        
        # Final summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('FINAL SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Total rides fetched: {stats["total_fetched"]}')
        if not dry_run:
            self.stdout.write(f'Created: {stats["created"]}')
            self.stdout.write(f'Updated: {stats["updated"]}')
        self.stdout.write(f'Skipped: {stats["skipped"]}')
        self.stdout.write(f'Errors: {stats["errors"]}')
        
        if stats['by_discipline']:
            self.stdout.write('')
            self.stdout.write('By Discipline:')
            for discipline, disc_stats in stats['by_discipline'].items():
                self.stdout.write(f'  {discipline.upper()}:')
                self.stdout.write(f'    Fetched: {disc_stats["fetched"]}')
                if not dry_run:
                    self.stdout.write(f'    Created: {disc_stats["created"]}')
                    self.stdout.write(f'    Updated: {disc_stats["updated"]}')
                self.stdout.write(f'    Errors: {disc_stats["errors"]}')
        
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('Sync complete!'))
