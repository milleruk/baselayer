"""
Celery tasks for background processing of workout sync operations.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from peloton.models import PelotonConnection
from peloton.services.peloton import PelotonClient, PelotonAPIError
from .models import Workout, RideDetail, WorkoutDetails, WorkoutPerformanceData, Instructor, WorkoutType
from challenges.utils import generate_peloton_url
from .views import _store_playlist_from_data, detect_class_type
from core.utils.redis_lock import RedisLock

logger = logging.getLogger(__name__)
User = get_user_model()


def store_ride_detail_from_api(client, ride_id, logger_instance=None):
    """
    Synchronous helper function to fetch and store ride details for a specific ride.
    This is extracted from fetch_ride_details_task for use in bulk operations.
    
    Args:
        client: Authenticated PelotonClient instance
        ride_id: Peloton ride/class ID
        logger_instance: Optional logger instance (defaults to module logger)
    
    Returns:
        dict: {'status': 'success'|'error', 'ride_detail_id': int, 'created': bool, 'message': str}
    """
    if logger_instance is None:
        logger_instance = logger
    
    try:
        logger_instance.info(f"Fetching ride details for ride_id {ride_id}")
        ride_details = client.fetch_ride_details(ride_id)
        ride_data = ride_details.get('ride', {})
        
        if not ride_data:
            logger_instance.warning(f"No ride data found for ride_id {ride_id}")
            return {'status': 'error', 'message': 'No ride data found'}
        
        # Extract class_type_ids and equipment_ids
        class_type_ids = ride_data.get('class_type_ids', [])
        if not isinstance(class_type_ids, list):
            class_type_ids = []
        
        equipment_ids = ride_data.get('equipment_ids', [])
        if not isinstance(equipment_ids, list):
            equipment_ids = []
        
        equipment_tags = ride_data.get('equipment_tags', [])
        if not isinstance(equipment_tags, list):
            equipment_tags = []
        
        # Generate standardized Peloton URL in UK format
        peloton_class_url = generate_peloton_url(ride_id) if ride_id else ''
        
        # Check if RideDetail already exists
        ride_detail, created = RideDetail.objects.get_or_create(
            peloton_ride_id=ride_id,
            defaults={
                'title': ride_data.get('title', ''),
                'description': ride_data.get('description', ''),
                'duration_seconds': ride_data.get('duration', 0),
                'workout_type': WorkoutType.objects.get_or_create(
                    slug=ride_data.get('fitness_discipline', 'other').lower(),
                    defaults={'name': ride_data.get('fitness_discipline', 'other').title()}
                )[0],
                'fitness_discipline': ride_data.get('fitness_discipline', ''),
                'fitness_discipline_display_name': ride_data.get('fitness_discipline_display_name', ''),
                'difficulty_rating_avg': ride_data.get('difficulty_rating_avg'),
                'difficulty_rating_count': ride_data.get('difficulty_rating_count', 0),
                'difficulty_level': ride_data.get('difficulty_level') or None,
                'overall_estimate': ride_data.get('overall_estimate'),
                'difficulty_estimate': ride_data.get('difficulty_estimate'),
                'image_url': ride_data.get('image_url', ''),
                'home_peloton_id': ride_data.get('home_peloton_id') or '',
                'peloton_class_url': peloton_class_url,
                'original_air_time': ride_data.get('original_air_time'),
                'scheduled_start_time': ride_data.get('scheduled_start_time'),
                'created_at_timestamp': ride_data.get('created_at'),
                'class_type': detect_class_type(ride_data, ride_details),
                'class_type_ids': class_type_ids,
                'equipment_ids': equipment_ids,
                'equipment_tags': equipment_tags,
                'target_metrics_data': ride_details.get('target_metrics_data', {}),
                'target_class_metrics': ride_details.get('target_class_metrics', {}),
                'pace_target_type': ride_details.get('pace_target_type'),
                'segments_data': ride_details.get('segments', {}),
                'is_archived': ride_data.get('is_archived', False),
                'is_power_zone_class': ride_data.get('is_power_zone_class', False),
            }
        )
        
        # Update instructor if needed
        instructor_id = ride_data.get('instructor_id')
        if instructor_id:
            instructor_obj = ride_data.get('instructor', {})
            instructor_name = instructor_obj.get('name') or instructor_obj.get('full_name') or 'Unknown Instructor'
            instructor, _ = Instructor.objects.get_or_create(
                peloton_id=instructor_id,
                defaults={
                    'name': instructor_name,
                    'image_url': instructor_obj.get('image_url', ''),
                }
            )
            if ride_detail.instructor != instructor:
                ride_detail.instructor = instructor
                ride_detail.save()
        
        # Store playlist if available
        playlist_data = ride_details.get('playlist')
        if playlist_data:
            _store_playlist_from_data(playlist_data, ride_detail, logger_instance)
        
        logger_instance.debug(f"Successfully processed ride details for ride_id {ride_id} ({'created' if created else 'updated'})")
        return {'status': 'success', 'ride_detail_id': ride_detail.id, 'created': created}
        
    except PelotonAPIError as e:
        logger_instance.error(f"Peloton API error fetching ride details for ride_id {ride_id}: {e}")
        return {'status': 'error', 'message': f'API error: {str(e)}'}
    except Exception as e:
        logger_instance.error(f"Error fetching ride details for ride_id {ride_id}: {e}", exc_info=True)
        return {'status': 'error', 'message': f'Error: {str(e)}'}


@shared_task(bind=True, max_retries=3)
def fetch_ride_details_task(self, user_id, ride_id, workout_id=None):
    """
    Background task to fetch and store ride details for a specific ride.
    
    Args:
        user_id: Django user ID
        ride_id: Peloton ride/class ID
        workout_id: Optional workout ID for logging context
    """
    try:
        # Acquire a short redis lock to avoid duplicate concurrent fetches for same ride
        lock_key = f'fetch:ride:{ride_id}'
        with RedisLock(lock_key, ttl=120) as acquired:
            if not acquired:
                logger.info(f"Fetch already in progress for ride {ride_id}, skipping")
                return {'status': 'skipped', 'reason': 'in_progress'}

            user = User.objects.get(pk=user_id)
        connection = PelotonConnection.objects.get(user=user, is_active=True)
        client = connection.get_client()
        
        logger.info(f"Fetching ride details for ride_id {ride_id} (user: {user.email})")
        ride_details = client.fetch_ride_details(ride_id)
        ride_data = ride_details.get('ride', {})
        
        if not ride_data:
            logger.warning(f"No ride data found for ride_id {ride_id}")
            return {'status': 'error', 'message': 'No ride data found'}
        
        # Check if RideDetail already exists
        ride_detail, created = RideDetail.objects.get_or_create(
            peloton_ride_id=ride_id,
            defaults={
                'title': ride_data.get('title', ''),
                'description': ride_data.get('description', ''),
                'duration_seconds': ride_data.get('duration', 0),
                'workout_type': WorkoutType.objects.get_or_create(
                    slug=ride_data.get('fitness_discipline', 'other').lower(),
                    defaults={'name': ride_data.get('fitness_discipline', 'other').title()}
                )[0],
                'fitness_discipline': ride_data.get('fitness_discipline', ''),
                'fitness_discipline_display_name': ride_data.get('fitness_discipline_display_name', ''),
                'difficulty_rating_avg': ride_data.get('difficulty_rating_avg'),
                'difficulty_rating_count': ride_data.get('difficulty_rating_count', 0),
                'difficulty_level': ride_data.get('difficulty_level') or None,
                'overall_estimate': ride_data.get('overall_estimate'),
                'difficulty_estimate': ride_data.get('difficulty_estimate'),
                'image_url': ride_data.get('image_url', ''),
                'home_peloton_id': ride_data.get('home_peloton_id') or '',
                'original_air_time': ride_data.get('original_air_time'),
                'scheduled_start_time': ride_data.get('scheduled_start_time'),
                'created_at_timestamp': ride_data.get('created_at'),
                'class_type': detect_class_type(ride_data, ride_details),
                'target_metrics_data': ride_details.get('target_metrics_data', {}),
                'target_class_metrics': ride_details.get('target_class_metrics', {}),
                'pace_target_type': ride_details.get('pace_target_type'),
                'segments_data': ride_details.get('segments', {}),
                'is_archived': ride_data.get('is_archived', False),
                'is_power_zone_class': ride_data.get('is_power_zone_class', False),
            }
        )
        
        # Update instructor if needed
        instructor_id = ride_data.get('instructor_id')
        if instructor_id:
            instructor_obj = ride_data.get('instructor', {})
            instructor_name = instructor_obj.get('name') or instructor_obj.get('full_name') or 'Unknown Instructor'
            instructor, _ = Instructor.objects.get_or_create(
                peloton_id=instructor_id,
                defaults={
                    'name': instructor_name,
                    'image_url': instructor_obj.get('image_url', ''),
                }
            )
            if ride_detail.instructor != instructor:
                ride_detail.instructor = instructor
                ride_detail.save()
        
        # Store playlist if available
        playlist_data = ride_details.get('playlist')
        if playlist_data:
            _store_playlist_from_data(playlist_data, ride_detail, logger)
        
        logger.info(f"Successfully processed ride details for ride_id {ride_id} ({'created' if created else 'updated'})")
        return {'status': 'success', 'ride_detail_id': ride_detail.id, 'created': created}
        
    except PelotonConnection.DoesNotExist:
        logger.error(f"No active Peloton connection found for user {user_id}")
        return {'status': 'error', 'message': 'No active connection'}
    except PelotonAPIError as e:
        logger.error(f"Peloton API error fetching ride details for ride_id {ride_id}: {e}")
        # Retry on API errors
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        logger.error(f"Error fetching ride details for ride_id {ride_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def fetch_performance_graph_task(self, user_id, workout_id, peloton_workout_id):
    """
    Background task to fetch and store performance graph data for a workout.
    
    Args:
        user_id: Django user ID
        workout_id: Django Workout model ID
        peloton_workout_id: Peloton workout ID
    """
    try:
        user = User.objects.get(pk=user_id)
        workout = Workout.objects.get(pk=workout_id, user=user)
        connection = PelotonConnection.objects.get(user=user, is_active=True)
        client = connection.get_client()
        
        logger.info(f"Fetching performance graph for workout {peloton_workout_id} (user: {user.email})")
        performance_graph = client.fetch_performance_graph(peloton_workout_id, every_n=5)
        
        # Extract metrics from performance graph
        summaries_array = performance_graph.get('summaries', [])
        metrics_array = performance_graph.get('metrics', [])
        metrics_dict = {}
        
        # Extract from summaries array
        for summary in summaries_array:
            if isinstance(summary, dict):
                slug = summary.get('slug')
                value = summary.get('value')
                if slug and value is not None:
                    metrics_dict[slug] = value
        
        # Extract avg/max from metrics array
        for metric in metrics_array:
            if isinstance(metric, dict):
                slug = metric.get('slug')
                avg_value = metric.get('average_value')
                max_value = metric.get('max_value')
                
                if slug:
                    avg_field_map = {
                        'output': 'avg_output',
                        'cadence': 'avg_cadence',
                        'resistance': 'avg_resistance',
                        'speed': 'avg_speed',
                        'heart_rate': 'avg_heart_rate',
                    }
                    max_field_map = {
                        'output': 'max_output',
                        'cadence': 'max_cadence',
                        'resistance': 'max_resistance',
                        'speed': 'max_speed',
                        'heart_rate': 'max_heart_rate',
                    }
                    
                    if avg_value is not None:
                        field_name = avg_field_map.get(slug, f'avg_{slug}')
                        metrics_dict[field_name] = avg_value
                    if max_value is not None:
                        field_name = max_field_map.get(slug, f'max_{slug}')
                        metrics_dict[field_name] = max_value
        
        # Check average_summaries
        average_summaries = performance_graph.get('average_summaries', [])
        for summary in average_summaries:
            if isinstance(summary, dict):
                slug = summary.get('slug')
                value = summary.get('value')
                if slug and value is not None:
                    avg_field_map = {
                        'output': 'avg_output',
                        'cadence': 'avg_cadence',
                        'resistance': 'avg_resistance',
                        'speed': 'avg_speed',
                        'heart_rate': 'avg_heart_rate',
                    }
                    field_name = avg_field_map.get(slug, f'avg_{slug}')
                    if field_name not in metrics_dict:
                        metrics_dict[field_name] = value
        
        # Update workout details
        if metrics_dict:
            details, details_created = WorkoutDetails.objects.get_or_create(workout=workout)
            details_updated = False
            
            # Helper to safely set float fields
            def set_float_field(field_name, value):
                try:
                    setattr(details, field_name, float(value))
                    return True
                except (ValueError, TypeError):
                    return False
            
            # Helper to safely set int fields
            def set_int_field(field_name, value):
                try:
                    setattr(details, field_name, int(float(value)))
                    return True
                except (ValueError, TypeError):
                    return False
            
            # TSS
            if 'tss' in metrics_dict:
                details_updated = set_float_field('tss', metrics_dict['tss']) or details_updated
            if 'tss_target' in metrics_dict:
                details_updated = set_float_field('tss_target', metrics_dict['tss_target']) or details_updated
            
            # Output metrics
            if 'total_output' in metrics_dict:
                details_updated = set_float_field('total_output', metrics_dict['total_output']) or details_updated
            if 'avg_output' in metrics_dict:
                details_updated = set_float_field('avg_output', metrics_dict['avg_output']) or details_updated
            if 'max_output' in metrics_dict:
                details_updated = set_float_field('max_output', metrics_dict['max_output']) or details_updated
            
            # Speed metrics
            if 'avg_speed' in metrics_dict:
                details_updated = set_float_field('avg_speed', metrics_dict['avg_speed']) or details_updated
            if 'max_speed' in metrics_dict:
                details_updated = set_float_field('max_speed', metrics_dict['max_speed']) or details_updated
            
            # Distance
            if 'distance' in metrics_dict:
                details_updated = set_float_field('distance', metrics_dict['distance']) or details_updated
            
            # Heart rate
            if 'avg_heart_rate' in metrics_dict:
                details_updated = set_int_field('avg_heart_rate', metrics_dict['avg_heart_rate']) or details_updated
            if 'max_heart_rate' in metrics_dict:
                details_updated = set_int_field('max_heart_rate', metrics_dict['max_heart_rate']) or details_updated
            
            # Cadence
            if 'avg_cadence' in metrics_dict:
                details_updated = set_int_field('avg_cadence', metrics_dict['avg_cadence']) or details_updated
            if 'max_cadence' in metrics_dict:
                details_updated = set_int_field('max_cadence', metrics_dict['max_cadence']) or details_updated
            
            # Resistance
            if 'avg_resistance' in metrics_dict:
                details_updated = set_float_field('avg_resistance', metrics_dict['avg_resistance']) or details_updated
            if 'max_resistance' in metrics_dict:
                details_updated = set_float_field('max_resistance', metrics_dict['max_resistance']) or details_updated
            
            # Calories
            if 'calories' in metrics_dict or 'total_calories' in metrics_dict:
                calories_value = metrics_dict.get('calories') or metrics_dict.get('total_calories')
                details_updated = set_int_field('total_calories', calories_value) or details_updated
            
            if details_updated:
                details.save()
                logger.info(f"Updated WorkoutDetails for workout {peloton_workout_id} with {len(metrics_dict)} metrics")
        
        # Store time-series performance data
        seconds_array = performance_graph.get('seconds_since_pedaling_start', [])
        if seconds_array and metrics_array:
            # Delete existing performance data
            WorkoutPerformanceData.objects.filter(workout=workout).delete()
            
            # Build metric values by slug
            metric_values_by_slug = {}
            for metric in metrics_array:
                slug = metric.get('slug')
                values = metric.get('values', [])
                if slug and values:
                    metric_values_by_slug[slug] = values
                
                # For running classes, speed might be in pace alternatives
                if slug == 'pace':
                    alternatives = metric.get('alternatives', [])
                    for alt in alternatives:
                        alt_slug = alt.get('slug')
                        alt_values = alt.get('values', [])
                        if alt_slug == 'speed' and alt_values and 'speed' not in metric_values_by_slug:
                            metric_values_by_slug['speed'] = alt_values
            
            # Create performance data entries
            performance_data_entries = []
            for idx, timestamp in enumerate(seconds_array):
                if not isinstance(timestamp, (int, float)):
                    continue
                
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
            
            # Bulk create
            if performance_data_entries:
                WorkoutPerformanceData.objects.bulk_create(performance_data_entries, ignore_conflicts=True)
                logger.info(f"Stored {len(performance_data_entries)} time-series data points for workout {peloton_workout_id}")
        
        logger.info(f"Successfully processed performance graph for workout {peloton_workout_id}")
        return {'status': 'success', 'workout_id': workout_id}
        
    except PelotonConnection.DoesNotExist:
        logger.error(f"No active Peloton connection found for user {user_id}")
        return {'status': 'error', 'message': 'No active connection'}
    except PelotonAPIError as e:
        logger.error(f"Peloton API error fetching performance graph for workout {peloton_workout_id}: {e}")
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        logger.error(f"Error fetching performance graph for workout {peloton_workout_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task
def batch_fetch_ride_details(user_id, ride_ids):
    """
    Batch task to fetch multiple ride details.
    Can be used to process multiple rides in parallel.
    
    Args:
        user_id: Django user ID
        ride_ids: List of Peloton ride IDs
    """
    results = []
    for ride_id in ride_ids:
        result = fetch_ride_details_task.delay(user_id, ride_id)
        results.append(result)
    return results


@shared_task
def batch_fetch_performance_graphs(user_id, workout_data_list):
    """
    Batch task to fetch multiple performance graphs.
    Can be used to process multiple workouts in parallel.
    
    Args:
        user_id: Django user ID
        workout_data_list: List of dicts with 'workout_id' and 'peloton_workout_id'
    """
    results = []
    for workout_data in workout_data_list:
        result = fetch_performance_graph_task.delay(
            user_id,
            workout_data['workout_id'],
            workout_data['peloton_workout_id']
        )
        results.append(result)
    return results
