"""
Service for handling class library filtering, searching, and pagination.
Encapsulates all the complex query logic from class_library view.
"""
from django.db.models import Q, Value, BigIntegerField
from django.db.models.functions import Coalesce
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ClassLibraryFilter:
    """Handles filtering, searching, and ordering of ride details for class library."""
    
    ALLOWED_TYPES = ['running', 'cycling', 'walking', 'rowing']
    ALLOWED_DISCIPLINES = ['running', 'run', 'cycling', 'ride', 'walking', 'rowing', 'row']
    STANDARD_DURATIONS = [5, 10, 15, 20, 30, 45, 60, 75, 90, 120]
    
    def __init__(self, queryset):
        """Initialize filter with a base queryset of RideDetail objects."""
        self.queryset = queryset
        self.filters = {}
    
    def apply_search(self, search_query):
        """Filter by search term (title or instructor name)."""
        if search_query and search_query.strip():
            self.queryset = self.queryset.filter(
                Q(title__icontains=search_query) |
                Q(instructor__name__icontains=search_query)
            )
            self.filters['search'] = search_query
        return self
    
    def apply_workout_type_filter(self, workout_type_slug):
        """Filter by workout type slug."""
        if workout_type_slug and workout_type_slug in self.ALLOWED_TYPES:
            self.queryset = self.queryset.filter(workout_type__slug=workout_type_slug)
            self.filters['workout_type'] = workout_type_slug
        return self
    
    def apply_instructor_filter(self, instructor_id):
        """Filter by instructor ID."""
        if instructor_id:
            try:
                self.queryset = self.queryset.filter(instructor_id=int(instructor_id))
                self.filters['instructor'] = instructor_id
            except (ValueError, TypeError):
                pass
        return self
    
    def apply_duration_filter(self, duration_minutes):
        """Filter by duration (±30 seconds tolerance)."""
        if duration_minutes:
            try:
                duration_min = int(duration_minutes)
                self.queryset = self.queryset.filter(
                    Q(duration_seconds__gte=duration_min * 60 - 30) &
                    Q(duration_seconds__lte=duration_min * 60 + 30)
                )
                self.filters['duration'] = duration_minutes
            except (ValueError, TypeError):
                pass
        return self
    
    def apply_year_filter(self, year):
        """Filter by year (converts to Unix timestamps)."""
        if year:
            try:
                year = int(year)
                start_timestamp = int(datetime(year, 1, 1, 0, 0, 0).timestamp())
                end_timestamp = int(datetime(year, 12, 31, 23, 59, 59).timestamp())
                self.queryset = self.queryset.filter(
                    original_air_time__gte=start_timestamp,
                    original_air_time__lte=end_timestamp
                )
                self.filters['year'] = year
            except (ValueError, TypeError):
                pass
        return self
    
    def apply_month_filter(self, year, month):
        """Filter by month (requires year)."""
        if year and month:
            try:
                year = int(year)
                month = int(month)
                if 1 <= month <= 12:
                    start_timestamp = int(datetime(year, month, 1, 0, 0, 0).timestamp())
                    # Get last day of month
                    if month == 12:
                        end_timestamp = int(datetime(year + 1, 1, 1, 0, 0, 0).timestamp()) - 1
                    else:
                        end_timestamp = int(datetime(year, month + 1, 1, 0, 0, 0).timestamp()) - 1
                    self.queryset = self.queryset.filter(
                        original_air_time__gte=start_timestamp,
                        original_air_time__lte=end_timestamp
                    )
                    self.filters['month'] = month
            except (ValueError, TypeError):
                pass
        return self
    
    def apply_ordering(self, order_by=None):
        """Apply ordering with proper NULL handling."""
        if not order_by or order_by not in [
            'original_air_time', '-original_air_time',
            'title', '-title',
            'duration_seconds', '-duration_seconds'
        ]:
            order_by = '-original_air_time'
        
        if order_by == '-original_air_time':
            # Descending: NULLs last using Coalesce with 0
            self.queryset = self.queryset.annotate(
                sort_air_time=Coalesce('original_air_time', Value(0, output_field=BigIntegerField()))
            ).order_by('-sort_air_time')
        elif order_by == 'original_air_time':
            # Ascending: NULLs last using Coalesce with large number
            self.queryset = self.queryset.annotate(
                sort_air_time=Coalesce('original_air_time', Value(9999999999999, output_field=BigIntegerField()))
            ).order_by('sort_air_time')
        else:
            self.queryset = self.queryset.order_by(order_by)
        
        self.filters['order_by'] = order_by
        return self
    
    def get_queryset(self):
        """Return the filtered queryset."""
        return self.queryset
    
    def get_filters(self):
        """Return applied filters dictionary."""
        return self.filters
    
    @staticmethod
    def get_available_years(base_queryset):
        """Extract unique years from rides with timestamps."""
        available_years = base_queryset.filter(
            original_air_time__isnull=False
        ).exclude(original_air_time=0).values_list('original_air_time', flat=True)
        
        years_set = set()
        for timestamp in available_years:
            try:
                ts = timestamp / 1000 if timestamp >= 1e12 else timestamp
                dt = datetime.fromtimestamp(ts)
                years_set.add(dt.year)
            except (ValueError, OSError, OverflowError):
                continue
        
        return sorted(list(years_set), reverse=True)
    
    @staticmethod
    def get_available_months(base_queryset, year):
        """Extract unique months for a given year."""
        if not year:
            return []
        
        try:
            year = int(year)
        except (ValueError, TypeError):
            return []
        
        months_set = set()
        year_rides = base_queryset.filter(
            original_air_time__isnull=False
        ).exclude(original_air_time=0)
        
        # Filter by year range
        start_timestamp = int(datetime(year, 1, 1, 0, 0, 0).timestamp())
        end_timestamp = int(datetime(year, 12, 31, 23, 59, 59).timestamp())
        year_rides = year_rides.filter(
            original_air_time__gte=start_timestamp,
            original_air_time__lte=end_timestamp
        ).values_list('original_air_time', flat=True)
        
        for timestamp in year_rides:
            try:
                ts = timestamp / 1000 if timestamp >= 1e12 else timestamp
                dt = datetime.fromtimestamp(ts)
                months_set.add(dt.month)
            except (ValueError, OSError, OverflowError):
                continue
        
        return sorted(list(months_set))
    
    @staticmethod
    def get_available_durations(base_queryset):
        """Get available durations combining standard and actual."""
        actual_durations = base_queryset.values_list('duration_seconds', flat=True).distinct()
        actual_durations_min = sorted(set(int(d / 60) for d in actual_durations if d))
        all_durations = sorted(set(ClassLibraryFilter.STANDARD_DURATIONS + actual_durations_min))
        return all_durations
