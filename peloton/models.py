from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os


def get_encryption_key():
    """Get or create encryption key for Peloton credentials"""
    key = getattr(settings, 'PELOTON_ENCRYPTION_KEY', None)
    if not key:
        # Use SECRET_KEY as fallback (not ideal but works for development)
        # In production, set PELOTON_ENCRYPTION_KEY in settings
        import hashlib
        secret = settings.SECRET_KEY.encode()
        key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    elif isinstance(key, str):
        # If it's a string, try to decode it as base64, otherwise use it directly
        try:
            key = base64.urlsafe_b64decode(key)
        except:
            # If decoding fails, treat it as a raw key and encode it
            key = key.encode()[:32].ljust(32, b'0')  # Pad or truncate to 32 bytes
            key = base64.urlsafe_b64encode(key)
    return key


class PelotonConnection(models.Model):
    """Stores Peloton API credentials and session for a user"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='peloton_api_connection'
    )
    
    # Encrypted credentials
    _encrypted_username = models.BinaryField(blank=True, null=True)
    _encrypted_password = models.BinaryField(blank=True, null=True)
    
    # OAuth2 Bearer Token (encrypted)
    _encrypted_bearer_token = models.BinaryField(blank=True, null=True)
    _encrypted_refresh_token = models.BinaryField(blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Legacy session ID support (deprecated but kept for migration)
    _encrypted_session_id = models.BinaryField(blank=True, null=True)
    
    # Peloton user ID from API
    peloton_user_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(blank=True, null=True)
    
    # Sync status tracking
    sync_in_progress = models.BooleanField(default=False, help_text="Whether a sync is currently in progress")
    sync_started_at = models.DateTimeField(blank=True, null=True, help_text="When the current sync started")
    sync_cooldown_until = models.DateTimeField(blank=True, null=True, help_text="When sync can be run again (60 min cooldown)")
    
    # Following data and cooldown (separate from workout sync)
    following_ids = models.JSONField(default=list, blank=True, help_text="List of Peloton user IDs that this user follows")
    following_last_sync_at = models.DateTimeField(blank=True, null=True, help_text="When following IDs were last fetched")
    following_cooldown_until = models.DateTimeField(blank=True, null=True, help_text="When following can be fetched again (60 min cooldown)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'peloton_connection'
        verbose_name = 'Peloton Connection'
        verbose_name_plural = 'Peloton Connections'
    
    def __str__(self):
        return f"Peloton Connection for {self.user.email}"
    
    def _encrypt(self, value: str) -> bytes:
        """Encrypt a string value"""
        if not value:
            return b''
        key = get_encryption_key()
        fernet = Fernet(key)
        return fernet.encrypt(value.encode())
    
    def _decrypt(self, encrypted_value: bytes) -> str:
        """Decrypt a bytes value to string"""
        if not encrypted_value:
            return ''
        key = get_encryption_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_value).decode()
    
    @property
    def username(self) -> str:
        """Get decrypted username"""
        return self._decrypt(self._encrypted_username) if self._encrypted_username else ''
    
    @username.setter
    def username(self, value: str):
        """Set encrypted username"""
        self._encrypted_username = self._encrypt(value) if value else None
    
    @property
    def password(self) -> str:
        """Get decrypted password"""
        return self._decrypt(self._encrypted_password) if self._encrypted_password else ''
    
    @password.setter
    def password(self, value: str):
        """Set encrypted password"""
        self._encrypted_password = self._encrypt(value) if value else None
    
    @property
    def bearer_token(self) -> str:
        """Get decrypted bearer token"""
        return self._decrypt(self._encrypted_bearer_token) if self._encrypted_bearer_token else ''
    
    @bearer_token.setter
    def bearer_token(self, value: str):
        """Set encrypted bearer token"""
        self._encrypted_bearer_token = self._encrypt(value) if value else None
    
    @property
    def refresh_token(self) -> str:
        """Get decrypted refresh token"""
        return self._decrypt(self._encrypted_refresh_token) if self._encrypted_refresh_token else ''
    
    @refresh_token.setter
    def refresh_token(self, value: str):
        """Set encrypted refresh token"""
        self._encrypted_refresh_token = self._encrypt(value) if value else None
    
    @property
    def session_id(self) -> str:
        """Get decrypted session ID (deprecated, kept for backward compatibility)"""
        return self._decrypt(self._encrypted_session_id) if self._encrypted_session_id else ''
    
    @session_id.setter
    def session_id(self, value: str):
        """Set encrypted session ID (deprecated)"""
        self._encrypted_session_id = self._encrypt(value) if value else None
    
    def get_client(self):
        """Get a PelotonClient instance with stored credentials"""
        from .services.peloton import PelotonClient
        from django.utils import timezone
        
        # Prefer bearer token if available and not expired
        if self.bearer_token:
            from datetime import timedelta
            # Check if token is expired (with 5 minute buffer)
            if not self.token_expires_at or self.token_expires_at > (timezone.now() + timedelta(minutes=5)):
                return PelotonClient(bearer_token=self.bearer_token)
        
        # Fall back to username/password authentication
        if self.username and self.password:
            return PelotonClient(username=self.username, password=self.password)
        else:
            raise ValueError("No Peloton credentials, bearer token, or session available")


def get_existing_peloton_connection(peloton_user_id: str, exclude_user_id: int | None = None):
    if not peloton_user_id:
        return None
    qs = PelotonConnection.objects.filter(peloton_user_id=str(peloton_user_id))
    if exclude_user_id:
        qs = qs.exclude(user_id=exclude_user_id)
    return qs.first()
