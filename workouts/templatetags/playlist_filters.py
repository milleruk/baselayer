from django import template
from urllib.parse import quote_plus

register = template.Library()


@register.filter
def format_song_time(seconds):
    """Format seconds into MM:SS format"""
    if not seconds:
        return "00:00"
    try:
        seconds = int(float(seconds))
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return "00:00"


@register.filter
def spotify_search_url(song):
    """
    Generate a Spotify search URL for a song.
    Uses song title and first artist name.
    """
    if not song:
        return None
    
    title = song.get('title', '')
    artists = song.get('artists', [])
    artist_name = artists[0].get('artist_name', '') if artists else ''
    
    # Create search query: "Artist Name - Song Title"
    if artist_name and title:
        query = f"{artist_name} {title}"
    elif title:
        query = title
    elif artist_name:
        query = artist_name
    else:
        return None
    
    # URL encode the query
    encoded_query = quote_plus(query)
    return f"https://open.spotify.com/search/{encoded_query}"


@register.filter
def format_duration_seconds(seconds):
    """Format seconds into MM:SS format"""
    if not seconds:
        return "0:00"
    try:
        seconds = int(float(seconds))
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    except (ValueError, TypeError):
        return "0:00"
