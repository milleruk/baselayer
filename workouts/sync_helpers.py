import logging
from .models import Playlist

# Known Peloton class_type IDs that should be treated as power zone classes
CLASS_TYPE_POWER_ZONE_IDS = {
	'4228e9e57bf64c518d58a1d0181760c4',
}

def detect_class_type(ride_data, ride_details=None):
	"""
	Detect class type from Peloton API data.
	Checks multiple sources: is_power_zone, pace_target_type, title keywords, segment types.
	Args:
		ride_data: Data from ride API response
		ride_details: Optional full ride details response (for target_metrics_data)
	Returns:
		str: Class type key (e.g., 'power_zone', 'pace_target', 'climb', etc.) or None
	"""
	# Priority 1: Check explicit flags
	if ride_data.get('is_power_zone_class') or ride_data.get('is_power_zone'):
		return 'power_zone'
	# Priority 1b: Check known Peloton class_type IDs that indicate Power Zone (e.g., "Pro Cyclist")
	try:
		class_type_ids = set()
		if isinstance(ride_data.get('class_type_ids'), (list, tuple)):
			class_type_ids.update([str(x) for x in ride_data.get('class_type_ids') if x])
		# Some API payloads include a list of class type objects under 'class_types'
		for ct in (ride_data.get('class_types') or []):
			if isinstance(ct, dict):
				cid = ct.get('id') or ct.get('peloton_id') or ct.get('pelotonId')
				if cid:
					class_type_ids.add(str(cid))
			elif isinstance(ct, str):
				class_type_ids.add(ct)
		# Single class_type object or id
		ct_obj = ride_data.get('class_type')
		if isinstance(ct_obj, dict):
			cid = ct_obj.get('id') or ct_obj.get('peloton_id') or ct_obj.get('pelotonId')
			if cid:
				class_type_ids.add(str(cid))
		elif ct_obj:
			class_type_ids.add(str(ct_obj))
		if ride_data.get('class_type_id'):
			class_type_ids.add(str(ride_data.get('class_type_id')))

		if class_type_ids & CLASS_TYPE_POWER_ZONE_IDS:
			return 'power_zone'
	except Exception:
		# Non-fatal — fall through to other detection heuristics
		pass
    
	# Priority 2: Check pace_target_type for running/walking
	pace_target_type = ride_data.get('pace_target_type') or (ride_details.get('pace_target_type') if ride_details else None)
	if pace_target_type:
		return 'pace_target'
    
	# Priority 3: Check target_metrics_data for segment types
	target_metrics_data = ride_data.get('target_metrics_data') or (ride_details.get('target_metrics_data') if ride_details else {})
	if target_metrics_data:
		target_metrics = target_metrics_data.get('target_metrics', [])
		segment_types = [s.get('segment_type', '').lower() for s in target_metrics if s.get('segment_type')]
		if 'power_zone' in segment_types:
			return 'power_zone'
		if any('pace' in st for st in segment_types):
			return 'pace_target'
    
	# Priority 4: Check title keywords (case-insensitive)
	title = (ride_data.get('title') or '').lower()
	fitness_discipline = (ride_data.get('fitness_discipline') or '').lower()
    
	# Check for power zone in title first (works across disciplines)
	if 'power zone' in title or ' pz ' in title or title.startswith('pz ') or title.endswith(' pz'):
		return 'power_zone'
    
	# Cycling class types
	if fitness_discipline in ['cycling', 'ride']:
		if 'climb' in title:
			return 'climb'
		if 'interval' in title:
			return 'intervals'
		if 'progression' in title:
			return 'progression'
		if 'low impact' in title:
			return 'low_impact'
		if 'beginner' in title:
			return 'beginner'
		if 'groove' in title:
			return 'groove'
		if 'pro cyclist' in title or 'pro cyclist' in title:
			return 'pro_cyclist'
		if 'live dj' in title:
			return 'live_dj'
		if 'peloton studio original' in title:
			return 'peloton_studio_original'
		if 'warm up' in title or 'warmup' in title:
			return 'warm_up'
		if 'cool down' in title or 'cooldown' in title:
			return 'cool_down'
		if 'music' in title or 'theme' in title:
			return 'music' if 'music' in title else 'theme'
    
	# Running class types
	elif fitness_discipline in ['running', 'run']:
		if 'pace' in title or 'pace target' in title:
			return 'pace_target'
		if 'speed' in title:
			return 'speed'
		if 'endurance' in title:
			return 'endurance'
		if 'walk' in title and 'run' in title:
			return 'walk_run'
		if 'form' in title or 'drill' in title:
			return 'form_drills'
		if 'warm up' in title or 'warmup' in title:
			return 'warm_up'
		if 'cool down' in title or 'cooldown' in title:
			return 'cool_down'
		if 'beginner' in title:
			return 'beginner'
		if 'music' in title or 'theme' in title:
			return 'music' if 'music' in title else 'theme'
    
	# Walking class types
	elif fitness_discipline in ['walking', 'walk']:
		if 'pace' in title or 'pace target' in title:
			return 'pace_target'
		if 'power walk' in title:
			return 'power_walk'
		if 'hiking' in title:
			return 'hiking'
		if 'warm up' in title or 'warmup' in title:
			return 'warm_up'
		if 'cool down' in title or 'cooldown' in title:
			return 'cool_down'
		if 'music' in title or 'theme' in title:
			return 'music' if 'music' in title else 'theme'
		if 'peloton studio original' in title:
			return 'peloton_studio_original'
    
	# Strength class types
	elif fitness_discipline in ['strength', 'strength_training']:
		if 'full body' in title or 'total strength' in title:
			return 'full_body'
		if 'core' in title:
			return 'core'
		if 'upper body' in title:
			return 'upper_body'
		if 'lower body' in title or 'glutes' in title or 'legs' in title:
			return 'lower_body'
		if 'strength basics' in title or ('basics' in title and 'strength' in title):
			return 'strength_basics'
		if ('arms' in title and 'light' in title) or 'arms & light weights' in title:
			return 'arms_light_weights'
		if 'strength for sport' in title or ('sport' in title and 'strength' in title):
			return 'strength_for_sport'
		if 'resistance bands' in title or 'resistance band' in title:
			return 'resistance_bands'
		if 'adaptive' in title:
			return 'adaptive'
		if 'barre' in title:
			return 'barre'
		if 'kettlebell' in title:
			return 'kettlebells'
		if 'boxing' in title or 'bootcamp' in title:
			return 'boxing_bootcamp'
		if 'bodyweight' in title or 'body weight' in title:
			return 'bodyweight'
		if 'warm up' in title or 'warmup' in title:
			return 'warm_up'
		if 'cool down' in title or 'cooldown' in title:
			return 'cool_down'
    
	# Yoga class types
	elif fitness_discipline in ['yoga']:
		if 'focus flow' in title:
			return 'focus_flow'
		if 'slow flow' in title:
			return 'slow_flow'
		if 'sculpt flow' in title:
			return 'sculpt_flow'
		if 'yoga + pilates' in title or 'yoga pilates' in title or 'pilates' in title:
			return 'yoga_pilates'
		if 'yin yoga' in title or 'yin' in title:
			return 'yin_yoga'
		if 'yoga anywhere' in title:
			return 'yoga_anywhere'
		if 'yoga basics' in title or 'basics' in title:
			return 'yoga_basics'
		if 'family' in title or 'pre/postnatal' in title or 'prenatal' in title or 'postnatal' in title:
			return 'family_pre_postnatal'
		if 'beyond the pose' in title:
			return 'beyond_the_pose'
		if 'power' in title:
			return 'power'
		if 'restorative' in title:
			return 'restorative'
		if 'morning' in title:
			return 'morning'
		if 'flow' in title:
			return 'flow'
		if 'theme' in title:
			return 'theme'
    
	# Meditation class types
	elif fitness_discipline in ['meditation']:
		if 'daily meditation' in title:
			return 'daily_meditation'
		if 'sleep' in title:
			return 'sleep'
		if 'relaxation' in title:
			return 'relaxation'
		if 'emotions' in title:
			return 'emotions'
		if 'meditation basics' in title or 'basics' in title:
			return 'meditation_basics'
		if 'breath' in title or 'breathing' in title:
			return 'breath'
		if 'mindfulness' in title:
			return 'mindfulness'
		if 'walking meditation' in title:
			return 'walking_meditation'
		if 'morning' in title:
			return 'morning'
		if 'theme' in title:
			return 'theme'
		if 'family' in title or 'pre/postnatal' in title or 'prenatal' in title or 'postnatal' in title:
			return 'family_pre_postnatal'
    
	# Default: return None (will be stored as empty/null)
	return None

def _store_playlist_from_data(playlist_data, ride_detail, logger, workout_num=None, workout_id=None):
	"""
	Helper function to store playlist data for a ride.
	playlist_data should come from ride_details response (data['playlist']).
	Returns True if playlist was stored successfully, False otherwise.
	"""
	if not playlist_data:
		return False
	try:
		# Extract playlist information
		peloton_playlist_id = playlist_data.get('id')
		songs = playlist_data.get('songs', [])
		top_artists = playlist_data.get('top_artists', [])
		top_albums = playlist_data.get('top_albums', [])
		stream_id = playlist_data.get('stream_id')
		stream_url = playlist_data.get('stream_url')
		# Create or update playlist
		playlist, playlist_created = Playlist.objects.update_or_create(
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
		log_prefix = f"Workout {workout_num} ({workout_id})" if workout_num and workout_id else "Playlist"
		if playlist_created:
			logger.info(f"{log_prefix}: ✓ Created Playlist with {len(songs)} songs")
		else:
			logger.debug(f"{log_prefix}: ↻ Updated Playlist")
		return True
	except Exception as e:
		# Playlist storage is optional - don't fail the whole sync if it fails
		log_prefix = f"Workout {workout_num} ({workout_id})" if workout_num and workout_id else "Playlist"
		logger.debug(f"{log_prefix}: Could not store playlist: {e}")
	return False
