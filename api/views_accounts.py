from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from accounts.models import Profile, WeightEntry, FTPEntry, PaceEntry
from .serializers_accounts import ProfileSerializer, WeightEntrySerializer, FTPEntrySerializer, PaceEntrySerializer


class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing user profiles. Only allows access to the authenticated user's profile.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only allow users to access their own profile
        return Profile.objects.filter(user=self.request.user)


class WeightEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing user weight entries.
    """
    serializer_class = WeightEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WeightEntry.objects.filter(user=self.request.user)


class FTPEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing user FTP (Functional Threshold Power) entries.
    """
    serializer_class = FTPEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FTPEntry.objects.filter(user=self.request.user)


class PaceEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing user running/walking pace entries.
    """
    serializer_class = PaceEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaceEntry.objects.filter(user=self.request.user)
