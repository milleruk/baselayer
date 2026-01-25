from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import date
import json

from .models import Workout, WorkoutType, Instructor, RideDetail, WorkoutDetails
from peloton.models import PelotonConnection


@login_required
def workout_history(request):
    """Display user's workout history with filtering and pagination"""
    # Get user's workouts - all class data comes from ride_detail via SQL joins
    workouts = Workout.objects.filter(user=request.user).select_related(
        'ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details'
    ).prefetch_related('performance_data')
    
    # Get Peloton connection status (from peloton app)
    try:
        peloton_connection = PelotonConnection.objects.get(user=request.user)
    except PelotonConnection.DoesNotExist:
        peloton_connection = None
    
    # Search query - all data comes from ride_detail via SQL joins
    search_query = request.GET.get('search', '').strip()
    if search_query:
        workouts = workouts.filter(
            Q(ride_detail__title__icontains=search_query) |
            Q(ride_detail__instructor__name__icontains=search_query)
        )
    
    # Filter by workout type - via ride_detail
    workout_type_filter = request.GET.get('type', '')
    if workout_type_filter:
        workouts = workouts.filter(ride_detail__workout_type__slug=workout_type_filter)
    
    # Filter by instructor - via ride_detail
    instructor_filter = request.GET.get('instructor', '')
    if instructor_filter:
        workouts = workouts.filter(ride_detail__instructor_id=instructor_filter)
    
    # Filter by duration - via ride_detail
    duration_filter = request.GET.get('duration', '')
    if duration_filter:
        try:
            duration_min = int(duration_filter)
            workouts = workouts.filter(
                Q(ride_detail__duration_seconds__gte=duration_min * 60 - 30) &
                Q(ride_detail__duration_seconds__lte=duration_min * 60 + 30)
            )
        except ValueError:
            pass
    
    # Filter by TSS (Training Stress Score) - via details
    tss_filter = request.GET.get('tss', '')
    if tss_filter:
        try:
            tss_value = float(tss_filter)
            workouts = workouts.filter(details__tss__gte=tss_value)
        except (ValueError, TypeError):
            pass
    
    # Ordering - title ordering uses ride_detail__title via SQL join
    order_by = request.GET.get('order_by', '-completed_date')
    if order_by in ['completed_date', '-completed_date', 'recorded_date', '-recorded_date']:
        workouts = workouts.order_by(order_by)
    elif order_by in ['title', '-title']:
        # Order by ride_detail title via SQL join
        workouts = workouts.order_by('ride_detail__title' if order_by == 'title' else '-ride_detail__title')
    else:
        workouts = workouts.order_by('-completed_date')
    
    # Pagination
    paginator = Paginator(workouts, 12)  # 12 workouts per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Add pagination flag for template
    is_paginated = page_obj.has_other_pages()
    
    # Get filter options - all data comes from ride_detail via SQL joins
    workout_types = WorkoutType.objects.all().order_by('name')
    # Get instructors from ride_details (all workouts use ride_detail now)
    instructors = Instructor.objects.filter(
        ride_details__workouts__user=request.user
    ).distinct().order_by('name')
    
    # Get unique durations for filter (from ride_detail) - standard durations
    standard_durations = [5, 10, 15, 20, 30, 45, 60, 75, 90, 120]
    # Also get actual durations from user's workouts
    actual_durations = Workout.objects.filter(
        user=request.user,
        ride_detail__isnull=False
    ).values_list('ride_detail__duration_seconds', flat=True).distinct()
    # Convert to minutes and combine with standard durations
    actual_durations_min = sorted(set(int(d / 60) for d in actual_durations if d))
    # Combine and deduplicate, keeping standard durations first
    all_durations = sorted(set(standard_durations + actual_durations_min))
    
    # Get fitness disciplines for tabs (cycling, running, rowing, etc.)
    fitness_disciplines = Workout.objects.filter(
        user=request.user,
        ride_detail__isnull=False
    ).values_list('ride_detail__fitness_discipline', flat=True).distinct()
    fitness_disciplines = [d for d in fitness_disciplines if d]  # Remove empty values
    
    context = {
        'workouts': page_obj,
        'workout_types': workout_types,
        'instructors': instructors,
        'durations': all_durations,
        'fitness_disciplines': fitness_disciplines,
        'peloton_connection': peloton_connection,
        'search_query': search_query,
        'workout_type_filter': workout_type_filter,
        'instructor_filter': instructor_filter,
        'duration_filter': duration_filter,
        'tss_filter': tss_filter,
        'order_by': order_by,
        'total_workouts': paginator.count,
        'is_paginated': is_paginated,
    }
    
    return render(request, 'workouts/history.html', context)


@login_required
def workout_detail(request, pk):
    """Display detailed view of a single workout"""
    workout = get_object_or_404(
        Workout.objects.select_related(
            'ride_detail', 'ride_detail__workout_type', 'ride_detail__instructor', 'details', 'user'
        ).prefetch_related('performance_data'),
        pk=pk,
        user=request.user
    )
    
    # Get performance data ordered by timestamp
    performance_data = workout.performance_data.all().order_by('timestamp')
    
    # Get user profile for target metrics calculations
    user_profile = request.user.profile
    
    # Prepare target metrics data based on class type
    target_metrics = None
    target_metrics_json = None
    if workout.ride_detail:
        ride_detail = workout.ride_detail
        
        if ride_detail.is_power_zone_class:
            # Power Zone class - get user's FTP for zone calculations
            user_ftp = user_profile.get_current_ftp()
            segments = ride_detail.get_power_zone_segments(user_ftp=user_ftp)
            zone_ranges = user_profile.get_power_zone_ranges() if user_ftp else None
            target_metrics = {
                'type': 'power_zone',
                'segments': segments,
                'zone_ranges': zone_ranges
            }
        elif ride_detail.fitness_discipline in ['running', 'walking']:
            # Running/Walking class - get user's pace zones
            pace_zones = user_profile.get_pace_zone_targets()
            segments = ride_detail.get_pace_segments(user_pace_zones=pace_zones)
            target_metrics = {
                'type': 'pace',
                'segments': segments,
                'pace_zones': pace_zones
            }
        else:
            # Standard cycling class - cadence/resistance ranges
            segments = ride_detail.get_cadence_resistance_segments()
            target_metrics = {
                'type': 'cadence_resistance',
                'segments': segments
            }
        
        # Convert to JSON for template
        if target_metrics:
            target_metrics_json = mark_safe(json.dumps(target_metrics))
    
    context = {
        'workout': workout,
        'performance_data': performance_data,
        'target_metrics': target_metrics,
        'target_metrics_json': target_metrics_json,
        'user_profile': user_profile,
    }
    
    return render(request, 'workouts/detail.html', context)


@login_required
def connect(request):
    """Redirect to Peloton connection page"""
    return redirect('peloton:connect')


@login_required
def sync_workouts(request):
    """Trigger manual sync of workouts from Peloton API"""
    if request.method != 'POST':
        return redirect('workouts:history')
    
    try:
        connection = PelotonConnection.objects.get(user=request.user)
    except PelotonConnection.DoesNotExist:
        messages.error(request, 'No Peloton connection found. Please connect your Peloton account first.')
        return redirect('workouts:history')
    
    try:
        from peloton.services.peloton import PelotonAPIError
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get client
        client = connection.get_client()
        
        # Get user ID
        if not connection.peloton_user_id:
            user_data = client.fetch_current_user()
            peloton_user_id = user_data.get('id')
            if peloton_user_id:
                connection.peloton_user_id = str(peloton_user_id)
                connection.save()
            else:
                messages.error(request, 'Could not determine Peloton user ID.')
                return redirect('workouts:history')
        else:
            peloton_user_id = connection.peloton_user_id
        
        # Fetch all workouts
        logger.info(f"Starting workout sync for user {request.user.email}, Peloton ID: {peloton_user_id}")
        workouts_synced = 0
        workouts_updated = 0
        workouts_skipped = 0
        total_processed = 0
        
        # Iterate through all workouts
        logger.info(f"Fetching workouts from Peloton API...")
        for workout_data in client.iter_user_workouts(peloton_user_id):
            total_processed += 1
            
            # Log progress every 50 workouts
            if total_processed % 50 == 0:
                logger.info(f"Progress: {total_processed} workouts processed ({workouts_synced} new, {workouts_updated} updated, {workouts_skipped} skipped)")
            try:
                peloton_workout_id = workout_data.get('id')
                if not peloton_workout_id:
                    workouts_skipped += 1
                    logger.warning(f"Workout {total_processed}: Skipping workout with no ID")
                    continue
                
                logger.info(f"Workout {total_processed}: Processing workout ID {peloton_workout_id}")
                
                # Log initial workout data structure for debugging
                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Initial workout_data keys: {list(workout_data.keys())}")
                if 'ride' in workout_data and workout_data.get('ride'):
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): ride keys: {list(workout_data.get('ride', {}).keys())}")
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): ride data: {str(workout_data.get('ride', {}))[:200]}")
                
                # Try to extract title and duration from workout_data first (might already be there)
                initial_title = None
                initial_duration_seconds = None
                ride_data = workout_data.get('ride', {})
                if ride_data:
                    initial_title = ride_data.get('title') or ride_data.get('name') or ride_data.get('class_title')
                    initial_duration_seconds = ride_data.get('duration') or ride_data.get('length')
                    if initial_title:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found title in initial workout_data: '{initial_title}'")
                    if initial_duration_seconds:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found duration in initial workout_data: {initial_duration_seconds}s")
                
                # Get or create workout type
                workout_type_slug = workout_data.get('fitness_discipline', '').lower()
                if not workout_type_slug:
                    workout_type_slug = 'other'
                
                # Map Peloton workout types to our workout types
                type_mapping = {
                    'cycling': 'cycling',
                    'running': 'running',
                    'walking': 'walking',
                    'yoga': 'yoga',
                    'strength': 'strength',
                    'stretching': 'stretching',
                    'meditation': 'meditation',
                    'cardio': 'cardio',
                }
                workout_type_slug = type_mapping.get(workout_type_slug, 'other')
                
                workout_type, _ = WorkoutType.objects.get_or_create(
                    slug=workout_type_slug,
                    defaults={'name': workout_type_slug.title()}
                )
                
                # Get or create instructor
                instructor = None
                instructor_data = workout_data.get('instructor', {})
                if instructor_data:
                    peloton_instructor_id = instructor_data.get('id')
                    instructor_name = instructor_data.get('name', 'Unknown')
                    if peloton_instructor_id:
                        instructor, _ = Instructor.objects.get_or_create(
                            peloton_id=peloton_instructor_id,
                            defaults={'name': instructor_name}
                        )
                        if instructor.image_url != instructor_data.get('image_url'):
                            instructor.image_url = instructor_data.get('image_url', '')
                            instructor.save()
                
                # Parse dates
                start_time = workout_data.get('start_time')
                if start_time:
                    if isinstance(start_time, (int, float)):
                        completed_date = datetime.fromtimestamp(start_time).date()
                    else:
                        # Try parsing as string
                        try:
                            completed_date = datetime.fromisoformat(str(start_time).replace('Z', '+00:00')).date()
                        except:
                            completed_date = timezone.now().date()
                else:
                    completed_date = timezone.now().date()
                
                # Step 1: Get ride_id from workout data
                ride_id = None
                if 'ride' in workout_data and workout_data.get('ride'):
                    ride_id = workout_data.get('ride', {}).get('id')
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found ride_id in workout_data: {ride_id}")
                
                # Step 2: Check if RideDetail already exists, if not fetch it FIRST
                ride_detail = None
                if ride_id:
                    # Check if we already have this ride detail
                    try:
                        ride_detail = RideDetail.objects.get(peloton_ride_id=ride_id)
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found existing RideDetail for ride_id {ride_id}: '{ride_detail.title}'")
                    except RideDetail.DoesNotExist:
                        # RideDetail doesn't exist, fetch it now BEFORE creating workout
                        logger.info(f"Workout {total_processed} ({peloton_workout_id}): RideDetail not found for ride_id {ride_id}, fetching ride details first...")
                        try:
                            ride_details = client.fetch_ride_details(ride_id)
                            ride_data = ride_details.get('ride', {})
                            if ride_data:
                                # We'll create RideDetail below after we have all the data
                                logger.info(f"Workout {total_processed} ({peloton_workout_id}): Successfully fetched ride details for ride_id {ride_id}")
                            else:
                                logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Ride details response missing 'ride' data for ride_id {ride_id}")
                                ride_details = None
                        except Exception as e:
                            logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch ride details for ride_id {ride_id}: {e}")
                            ride_details = None
                else:
                    # No ride_id yet, try to get it from detailed workout
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No ride_id in workout_data, fetching detailed workout to get ride_id...")
                    try:
                        detailed_workout = client.fetch_workout(peloton_workout_id)
                        ride_id = detailed_workout.get('ride', {}).get('id') or detailed_workout.get('ride_id')
                        if ride_id:
                            logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found ride_id in detailed_workout: {ride_id}")
                            # Check if RideDetail exists
                            try:
                                ride_detail = RideDetail.objects.get(peloton_ride_id=ride_id)
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found existing RideDetail for ride_id {ride_id}")
                            except RideDetail.DoesNotExist:
                                # Fetch ride details
                                logger.info(f"Workout {total_processed} ({peloton_workout_id}): Fetching ride details for ride_id {ride_id}...")
                                try:
                                    ride_details = client.fetch_ride_details(ride_id)
                                    ride_data = ride_details.get('ride', {})
                                    if not ride_data:
                                        ride_details = None
                                except Exception as e:
                                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch ride details: {e}")
                                    ride_details = None
                        else:
                            logger.warning(f"Workout {total_processed} ({peloton_workout_id}): No ride_id found in detailed workout")
                            detailed_workout = None
                            ride_details = None
                    except Exception as e:
                        logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch detailed workout: {e}")
                        detailed_workout = None
                        ride_details = None
                
                # Step 3: Create or update RideDetail if we have ride_details and it doesn't exist yet
                if ride_id and not ride_detail and 'ride_details' in locals() and ride_details:
                    ride_data = ride_details.get('ride', {})
                    if ride_data:
                        logger.info(f"Workout {total_processed} ({peloton_workout_id}): Creating RideDetail for ride_id {ride_id}...")
                        
                        # Extract instructor from ride_details (more reliable than workout_data)
                        # ride_details has: ride_data['instructor_id'] and ride_data['instructor'] object
                        ride_instructor = None
                        instructor_id_from_ride = ride_data.get('instructor_id')
                        instructor_obj_from_ride = ride_data.get('instructor', {})
                        
                        if instructor_id_from_ride:
                            # Try to get instructor by peloton_id
                            try:
                                ride_instructor = Instructor.objects.get(peloton_id=instructor_id_from_ride)
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found existing instructor: {ride_instructor.name}")
                            except Instructor.DoesNotExist:
                                # Create instructor from ride_details instructor object
                                if instructor_obj_from_ride:
                                    instructor_name = instructor_obj_from_ride.get('name') or instructor_obj_from_ride.get('full_name') or 'Unknown Instructor'
                                    instructor_image = instructor_obj_from_ride.get('image_url') or ''
                                    ride_instructor, created = Instructor.objects.get_or_create(
                                        peloton_id=instructor_id_from_ride,
                                        defaults={
                                            'name': instructor_name,
                                            'image_url': instructor_image,
                                        }
                                    )
                                    if created:
                                        logger.info(f"Workout {total_processed} ({peloton_workout_id}): Created new instructor: {ride_instructor.name}")
                                    else:
                                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found instructor after creation: {ride_instructor.name}")
                                else:
                                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): instructor_id {instructor_id_from_ride} found but no instructor object in ride_details")
                        
                        # Fallback to instructor from workout_data if not found in ride_details
                        if not ride_instructor:
                            ride_instructor = instructor
                            if ride_instructor:
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Using instructor from workout_data: {ride_instructor.name}")
                        
                        # Extract equipment tags
                        equipment_tags = ride_data.get('equipment_tags', [])
                        if not isinstance(equipment_tags, list):
                            equipment_tags = []
                        
                        # Extract class type IDs
                        class_type_ids = ride_data.get('class_type_ids', [])
                        if not isinstance(class_type_ids, list):
                            class_type_ids = []
                        
                        # Extract equipment IDs
                        equipment_ids = ride_data.get('equipment_ids', [])
                        if not isinstance(equipment_ids, list):
                            equipment_ids = []
                        
                        # Generate class URL
                        peloton_class_url = f"https://members.onepeloton.com/classes/cycling/{ride_id}" if ride_id else ''
                        # Try to determine discipline from ride_data
                        fitness_discipline = ride_data.get('fitness_discipline', '')
                        if fitness_discipline:
                            # Map discipline to URL path
                            discipline_paths = {
                                'cycling': 'cycling',
                                'running': 'treadmill',
                                'walking': 'walking',
                                'yoga': 'yoga',
                                'strength': 'strength',
                                'stretching': 'stretching',
                                'meditation': 'meditation',
                                'cardio': 'cardio',
                            }
                            path = discipline_paths.get(fitness_discipline, 'cycling')
                            peloton_class_url = f"https://members.onepeloton.com/classes/{path}/{ride_id}"
                        
                        ride_detail, ride_detail_created = RideDetail.objects.update_or_create(
                            peloton_ride_id=ride_id,
                            defaults={
                                'title': ride_data.get('title', ''),
                                'description': ride_data.get('description', ''),
                                'duration_seconds': ride_data.get('duration', 0),
                                'workout_type': workout_type,
                                'instructor': ride_instructor,  # Use instructor from ride_details
                                'fitness_discipline': ride_data.get('fitness_discipline', ''),
                                'fitness_discipline_display_name': ride_data.get('fitness_discipline_display_name', ''),
                                'difficulty_rating_avg': ride_data.get('difficulty_rating_avg'),
                                'difficulty_rating_count': ride_data.get('difficulty_rating_count', 0),
                                'difficulty_level': ride_data.get('difficulty_level') or None,
                                'overall_estimate': ride_data.get('overall_estimate'),
                                'difficulty_estimate': ride_data.get('difficulty_estimate'),
                                'image_url': ride_data.get('image_url', ''),
                                'home_peloton_id': ride_data.get('home_peloton_id', ''),
                                'original_air_time': ride_data.get('original_air_time'),
                                'scheduled_start_time': ride_data.get('scheduled_start_time'),
                                'created_at_timestamp': ride_data.get('created_at'),
                                'class_type_ids': class_type_ids,
                                'equipment_ids': equipment_ids,
                                'equipment_tags': equipment_tags,
                                'content_format': ride_data.get('content_format', ''),
                                'content_provider': ride_data.get('content_provider', ''),
                                'has_closed_captions': ride_data.get('has_closed_captions', False),
                                'is_archived': ride_data.get('is_archived', False),
                                'is_power_zone_class': ride_data.get('is_power_zone_class', False),
                                'peloton_class_url': peloton_class_url,
                                # Store target metrics from ride_details (not ride_data)
                                'target_metrics_data': ride_details.get('target_metrics_data', {}),
                                'target_class_metrics': ride_details.get('target_class_metrics', {}),
                                'pace_target_type': ride_details.get('pace_target_type'),
                            }
                        )
                        if ride_detail_created:
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): ✓ Created RideDetail: '{ride_detail.title}'")
                        else:
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): ↻ Updated RideDetail: '{ride_detail.title}'")
                
                # Step 4: Now fetch detailed workout for metrics (if we haven't already)
                if 'detailed_workout' not in locals():
                    try:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Fetching detailed workout for metrics...")
                        detailed_workout = client.fetch_workout(peloton_workout_id)
                    except Exception as e:
                        logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch detailed workout: {e}")
                        detailed_workout = None
                
                # Step 5: Extract title, duration, etc. from ride_detail if available, otherwise from other sources
                if ride_detail:
                    # Use data from RideDetail (most reliable)
                    title = ride_detail.title
                    duration_seconds = ride_detail.duration_seconds
                    duration_minutes = ride_detail.duration_minutes
                    description = ride_detail.description
                    difficulty_rating = ride_detail.difficulty_rating_avg
                    total_ratings = ride_detail.difficulty_rating_count
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Using data from RideDetail: '{title}' ({duration_minutes}min)")
                else:
                    # Fallback: extract from ride_details or detailed_workout
                    if 'ride_details' in locals() and ride_details:
                        ride_data = ride_details.get('ride', {})
                        title = ride_data.get('title') or ride_details.get('title') or workout_data.get('name', f"{workout_type.name} Workout")
                        duration_seconds = ride_data.get('duration') or ride_data.get('length') or 0
                        duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                        description = ride_data.get('description', '')
                        difficulty_rating = ride_data.get('difficulty_rating_avg')
                        total_ratings = ride_data.get('difficulty_rating_count', 0)
                    elif 'detailed_workout' in locals() and detailed_workout:
                        ride_data = detailed_workout.get('ride', {})
                        title = ride_data.get('title') or detailed_workout.get('name') or workout_data.get('name', f"{workout_type.name} Workout")
                        duration_seconds = ride_data.get('duration') or ride_data.get('length') or 0
                        duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                        description = detailed_workout.get('description', '')
                        difficulty_rating = None
                        total_ratings = 0
                    else:
                        # Last resort: use workout_data
                        title = initial_title or workout_data.get('name') or workout_data.get('title') or f"{workout_type.name} Workout"
                        duration_seconds = initial_duration_seconds or workout_data.get('duration') or 0
                        duration_minutes = int(duration_seconds / 60) if duration_seconds else 0
                        description = ''
                        difficulty_rating = None
                        total_ratings = 0
                    
                    logger.info(f"Workout {total_processed} ({peloton_workout_id}): Using fallback data - title: '{title}', duration: {duration_minutes}min")
                
                # Get Peloton workout URL - use workout ID format (profile/workouts/{id})
                peloton_url = None
                if peloton_workout_id:
                    # The workout URL format is: /profile/workouts/{workout_id}
                    peloton_url = f"https://members.onepeloton.com/profile/workouts/{peloton_workout_id}"
                
                # Create or update workout
                # NOTE: ride_detail is REQUIRED for new workouts - all class data comes from there via SQL joins
                # We don't store duplicate data (title, duration, instructor, etc.) in Workout model
                if not ride_detail:
                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Cannot create workout without ride_detail. Skipping.")
                    workouts_skipped += 1
                    continue
                
                workout, created = Workout.objects.update_or_create(
                    peloton_workout_id=peloton_workout_id,
                    user=request.user,
                    defaults={
                        'ride_detail': ride_detail,  # REQUIRED - all class data comes from here
                        'peloton_url': peloton_url,
                        'recorded_date': completed_date,
                        'completed_date': completed_date,
                        # No duplicate storage - title, duration, instructor, etc. come from ride_detail via joins
                    }
                )
                
                if created:
                    workouts_synced += 1
                    logger.info(f"Workout {total_processed} ({peloton_workout_id}): ✓ Created - '{ride_detail.title}' ({ride_detail.duration_minutes}min, {ride_detail.workout_type.name})")
                else:
                    workouts_updated += 1
                    logger.info(f"Workout {total_processed} ({peloton_workout_id}): ↻ Updated - '{ride_detail.title}' ({ride_detail.duration_minutes}min, {ride_detail.workout_type.name})")
                
                # Fetch performance graph to get detailed metrics (TSS, cadence, resistance, etc.)
                # This endpoint contains the actual workout metrics
                try:
                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Fetching performance graph for metrics (every_n=5)...")
                    performance_graph = client.fetch_performance_graph(peloton_workout_id, every_n=5)
                    
                    # Extract metrics from performance graph
                    # The performance graph has a 'summaries' array with summary metrics (total_output, etc.)
                    # and a 'metrics' array with time-series data (for avg/max calculations)
                    summaries_array = performance_graph.get('summaries', [])
                    metrics_array = performance_graph.get('metrics', [])
                    metrics_dict = {}
                    
                    # Extract from summaries array (has slug and value)
                    for summary in summaries_array:
                        if isinstance(summary, dict):
                            slug = summary.get('slug')
                            value = summary.get('value')
                            
                            if slug and value is not None:
                                metrics_dict[slug] = value
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found summary metric {slug} = {value}")
                    
                    # Extract avg/max from metrics array (time-series data with average_value and max_value)
                    for metric in metrics_array:
                        if isinstance(metric, dict):
                            slug = metric.get('slug')
                            avg_value = metric.get('average_value')
                            max_value = metric.get('max_value')
                            
                            if slug:
                                # Map slug to our field names
                                if avg_value is not None:
                                    # Map common slugs to our field names
                                    avg_field_map = {
                                        'output': 'avg_output',
                                        'cadence': 'avg_cadence',
                                        'resistance': 'avg_resistance',
                                        'speed': 'avg_speed',
                                        'heart_rate': 'avg_heart_rate',
                                    }
                                    field_name = avg_field_map.get(slug, f'avg_{slug}')
                                    metrics_dict[field_name] = avg_value
                                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found avg metric {slug} -> {field_name} = {avg_value}")
                                
                                if max_value is not None:
                                    max_field_map = {
                                        'output': 'max_output',
                                        'cadence': 'max_cadence',
                                        'resistance': 'max_resistance',
                                        'speed': 'max_speed',
                                        'heart_rate': 'max_heart_rate',
                                    }
                                    field_name = max_field_map.get(slug, f'max_{slug}')
                                    metrics_dict[field_name] = max_value
                                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found max metric {slug} -> {field_name} = {max_value}")
                    
                    # Also check for average_summaries (if present)
                    average_summaries = performance_graph.get('average_summaries', [])
                    for summary in average_summaries:
                        if isinstance(summary, dict):
                            slug = summary.get('slug')
                            value = summary.get('value')
                            if slug and value is not None:
                                # These are typically averages
                                avg_field_map = {
                                    'output': 'avg_output',
                                    'cadence': 'avg_cadence',
                                    'resistance': 'avg_resistance',
                                    'speed': 'avg_speed',
                                    'heart_rate': 'avg_heart_rate',
                                }
                                field_name = avg_field_map.get(slug, f'avg_{slug}')
                                if field_name not in metrics_dict:  # Don't overwrite if already set
                                    metrics_dict[field_name] = value
                                    logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found average_summary {slug} -> {field_name} = {value}")
                    
                    # Also check detailed_workout for any metrics that might be there (fallback)
                    if 'detailed_workout' in locals() and detailed_workout:
                        top_level_metrics = ['total_output', 'avg_output', 'max_output', 'distance', 'total_calories', 
                                            'avg_heart_rate', 'max_heart_rate', 'avg_cadence', 'max_cadence', 
                                            'avg_resistance', 'max_resistance', 'avg_speed', 'max_speed', 'tss', 'tss_target']
                        for key in top_level_metrics:
                            if key in detailed_workout and key not in metrics_dict:
                                metrics_dict[key] = detailed_workout[key]
                                logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Found metric in detailed_workout {key} = {detailed_workout[key]}")
                    
                    # Update workout details with extracted metrics
                    if metrics_dict:
                        details, details_created = WorkoutDetails.objects.get_or_create(workout=workout)
                        details_updated = False
                        
                        # TSS (might be in detailed_workout, not performance graph)
                        if 'tss' in metrics_dict:
                            try:
                                details.tss = float(metrics_dict['tss'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'tss_target' in metrics_dict:
                            try:
                                details.tss_target = float(metrics_dict['tss_target'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Output metrics
                        if 'total_output' in metrics_dict:
                            try:
                                details.total_output = float(metrics_dict['total_output'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'avg_output' in metrics_dict:
                            try:
                                details.avg_output = float(metrics_dict['avg_output'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_output' in metrics_dict:
                            try:
                                details.max_output = float(metrics_dict['max_output'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Speed metrics
                        if 'avg_speed' in metrics_dict:
                            try:
                                details.avg_speed = float(metrics_dict['avg_speed'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_speed' in metrics_dict:
                            try:
                                details.max_speed = float(metrics_dict['max_speed'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Distance
                        if 'distance' in metrics_dict:
                            try:
                                details.distance = float(metrics_dict['distance'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Heart rate (might be in metrics array as 'heart_rate')
                        if 'avg_heart_rate' in metrics_dict:
                            try:
                                details.avg_heart_rate = int(float(metrics_dict['avg_heart_rate']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_heart_rate' in metrics_dict:
                            try:
                                details.max_heart_rate = int(float(metrics_dict['max_heart_rate']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Cadence
                        if 'avg_cadence' in metrics_dict:
                            try:
                                details.avg_cadence = int(float(metrics_dict['avg_cadence']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_cadence' in metrics_dict:
                            try:
                                details.max_cadence = int(float(metrics_dict['max_cadence']))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Resistance
                        if 'avg_resistance' in metrics_dict:
                            try:
                                details.avg_resistance = float(metrics_dict['avg_resistance'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        if 'max_resistance' in metrics_dict:
                            try:
                                details.max_resistance = float(metrics_dict['max_resistance'])
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        # Calories (from summaries, slug is 'calories')
                        if 'calories' in metrics_dict or 'total_calories' in metrics_dict:
                            try:
                                calories_value = metrics_dict.get('calories') or metrics_dict.get('total_calories')
                                details.total_calories = int(float(calories_value))
                                details_updated = True
                            except (ValueError, TypeError):
                                pass
                        
                        if details_updated:
                            details.save()
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): WorkoutDetails {'created' if details_created else 'updated'} with {len(metrics_dict)} metrics")
                        else:
                            logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No metrics to update")
                    
                    # Store time-series performance data in WorkoutPerformanceData
                    # The performance graph has 'seconds_since_pedaling_start' and 'metrics' with 'values' arrays
                    seconds_array = performance_graph.get('seconds_since_pedaling_start', [])
                    if seconds_array and metrics_array:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): Storing time-series performance data...")
                        
                        # Delete existing performance data for this workout
                        from .models import WorkoutPerformanceData
                        WorkoutPerformanceData.objects.filter(workout=workout).delete()
                        
                        # Build a dict of metric values by slug for easier access
                        metric_values_by_slug = {}
                        for metric in metrics_array:
                            slug = metric.get('slug')
                            values = metric.get('values', [])
                            if slug and values:
                                metric_values_by_slug[slug] = values
                        
                        # Create performance data entries for each timestamp
                        performance_data_entries = []
                        for idx, timestamp in enumerate(seconds_array):
                            if not isinstance(timestamp, (int, float)):
                                continue
                            
                            # Extract values for this timestamp from each metric
                            perf_data = WorkoutPerformanceData(
                                workout=workout,
                                timestamp=int(timestamp),
                                output=metric_values_by_slug.get('output', [None])[idx] if idx < len(metric_values_by_slug.get('output', [])) else None,
                                cadence=int(metric_values_by_slug.get('cadence', [None])[idx]) if idx < len(metric_values_by_slug.get('cadence', [])) and metric_values_by_slug.get('cadence', [None])[idx] is not None else None,
                                resistance=metric_values_by_slug.get('resistance', [None])[idx] if idx < len(metric_values_by_slug.get('resistance', [])) else None,
                                speed=metric_values_by_slug.get('speed', [None])[idx] if idx < len(metric_values_by_slug.get('speed', [])) else None,
                                heart_rate=int(metric_values_by_slug.get('heart_rate', [None])[idx]) if idx < len(metric_values_by_slug.get('heart_rate', [])) and metric_values_by_slug.get('heart_rate', [None])[idx] is not None else None,
                            )
                            performance_data_entries.append(perf_data)
                        
                        # Bulk create performance data
                        if performance_data_entries:
                            WorkoutPerformanceData.objects.bulk_create(performance_data_entries, ignore_conflicts=True)
                            logger.info(f"Workout {total_processed} ({peloton_workout_id}): Stored {len(performance_data_entries)} time-series data points")
                        else:
                            logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No time-series data to store")
                    else:
                        logger.debug(f"Workout {total_processed} ({peloton_workout_id}): No time-series data available (seconds_array: {len(seconds_array) if seconds_array else 0}, metrics_array: {len(metrics_array) if metrics_array else 0})")
                        
                except Exception as e:
                    logger.warning(f"Workout {total_processed} ({peloton_workout_id}): Could not fetch performance graph for metrics: {e}")
                    # Continue without metrics - workout is still created
                
            except Exception as e:
                workouts_skipped += 1
                logger.error(f"Workout {total_processed} ({workout_data.get('id', 'unknown')}): ✗ Error syncing workout: {e}", exc_info=True)
                continue
        
        # Update connection last sync time
        connection.last_sync_at = timezone.now()
        connection.save()
        
        # Also update profile sync time
        if hasattr(request.user, 'profile'):
            request.user.profile.peloton_last_synced_at = timezone.now()
            request.user.profile.save()
        
        success_message = f'Successfully synced {workouts_synced} new workouts and updated {workouts_updated} existing workouts!'
        messages.success(request, success_message)
        logger.info(f"Workout sync completed for user {request.user.email}:")
        logger.info(f"  - Total processed: {total_processed}")
        logger.info(f"  - New workouts: {workouts_synced}")
        logger.info(f"  - Updated workouts: {workouts_updated}")
        logger.info(f"  - Skipped/errors: {workouts_skipped}")
        logger.info(f"  - Success rate: {((workouts_synced + workouts_updated) / total_processed * 100) if total_processed > 0 else 0:.1f}%")
        
        # If AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': success_message,
                'workouts_synced': workouts_synced,
                'workouts_updated': workouts_updated,
            })
        
    except PelotonAPIError as e:
        logger.error(f"Peloton API error during sync: {e}", exc_info=True)
        error_message = f'Peloton API error: {str(e)}'
        messages.error(request, error_message)
        
        # If AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_message,
            }, status=400)
    except Exception as e:
        logger.error(f"Error syncing workouts: {e}", exc_info=True)
        error_message = f'Error syncing workouts: {str(e)}'
        messages.error(request, error_message)
        
        # If AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_message,
            }, status=500)
    
    return redirect('workouts:history')


@login_required
@require_http_methods(["GET"])
def sync_status(request):
    """Return sync status for AJAX polling"""
    try:
        connection = PelotonConnection.objects.get(user=request.user)
        status = {
            'connected': True,
            'last_sync_at': connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            'workout_count': Workout.objects.filter(user=request.user).count(),
        }
    except PelotonConnection.DoesNotExist:
        status = {
            'connected': False,
            'last_sync_at': None,
            'workout_count': 0,
        }
    
    return JsonResponse(status)
