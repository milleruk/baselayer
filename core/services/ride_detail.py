"""
Ride detail service for class library integration.

Provides synchronous local database lookups and async queue management
for Peloton class (ride detail) synchronization.
"""
from workouts.models import RideDetail
from core.models import RideSyncQueue


def get_or_check_ride_detail(class_id):
    """
    Synchronously check if a ride detail exists in the local database.
    
    This function performs NO API calls - it only queries the local RideDetail table.
    
    Args:
        class_id (str): The Peloton class ID to look up
    
    Returns:
        tuple: (RideDetail object or None, bool is_found)
            - RideDetail object if found
            - bool: True if found, False if not found
    
    Examples:
        ride_detail, found = get_or_check_ride_detail('abc123')
        if found:
            print(f"Class found: {ride_detail.name}")
        else:
            print(f"Class {class_id} not in library yet")
    """
    if not class_id or not isinstance(class_id, str):
        return None, False
    
    class_id = class_id.strip()
    if not class_id:
        return None, False
    
    try:
        ride_detail = RideDetail.objects.get(peloton_id=class_id)
        return ride_detail, True
    except RideDetail.DoesNotExist:
        return None, False
    except Exception as e:
        # Log but don't fail on other DB errors
        print(f"Error looking up RideDetail {class_id}: {e}")
        return None, False


def queue_missing_rides(class_ids):
    """
    Create RideSyncQueue entries for any ride details not found locally.
    
    This function checks each class_id against the local RideDetail table.
    For any IDs not found, creates a RideSyncQueue entry with status='pending'
    to be processed by the background sync task.
    
    Args:
        class_ids (list): List of Peloton class IDs to check
    
    Returns:
        dict: {
            'found_count': int,
            'missing_count': int,
            'queued_count': int,  # New entries created
            'already_queued_count': int,  # Already in queue
            'missing_ids': list of IDs not found locally
        }
    
    Examples:
        result = queue_missing_rides(['abc123', 'def456'])
        if result['missing_count'] > 0:
            print(f"Queued {result['queued_count']} classes for sync")
    """
    if not class_ids:
        return {
            'found_count': 0,
            'missing_count': 0,
            'queued_count': 0,
            'already_queued_count': 0,
            'missing_ids': []
        }
    
    # Normalize and deduplicate
    class_ids = list(set(str(cid).strip() for cid in class_ids if cid))
    
    # Find which ones are missing locally
    found_ids = set(
        RideDetail.objects.filter(peloton_ride_id__in=class_ids)
        .values_list('peloton_ride_id', flat=True)
    )
    missing_ids = [cid for cid in class_ids if cid not in found_ids]
    
    # Create queue entries for missing IDs (only if not already queued)
    queued_count = 0
    already_queued_count = 0
    
    for class_id in missing_ids:
        obj, created = RideSyncQueue.objects.get_or_create(
            class_id=class_id,
            defaults={'status': 'pending'}
        )
        if created:
            queued_count += 1
        else:
            already_queued_count += 1
    
    return {
        'found_count': len(found_ids),
        'missing_count': len(missing_ids),
        'queued_count': queued_count,
        'already_queued_count': already_queued_count,
        'missing_ids': missing_ids
    }


def get_pending_ride_syncs(limit=None):
    """
    Retrieve all pending ride syncs from the queue.
    
    Args:
        limit (int, optional): Maximum number of entries to return
    
    Returns:
        QuerySet: RideSyncQueue entries with status='pending'
    """
    qs = RideSyncQueue.objects.filter(status='pending').order_by('created_at')
    if limit:
        qs = qs[:limit]
    return qs


def get_sync_queue_status():
    """
    Get a summary of the current sync queue status.
    
    Returns:
        dict: {
            'pending_count': int,
            'synced_count': int,
            'failed_count': int,
            'total_count': int
        }
    """
    return {
        'pending_count': RideSyncQueue.objects.filter(status='pending').count(),
        'synced_count': RideSyncQueue.objects.filter(status='synced').count(),
        'failed_count': RideSyncQueue.objects.filter(status='failed').count(),
        'total_count': RideSyncQueue.objects.count(),
    }
