from django.contrib import admin
from .models import PelotonConnection


@admin.register(PelotonConnection)
class PelotonConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'peloton_user_id', 'is_active', 'last_sync_at', 'created_at')
    list_filter = ('is_active', 'created_at', 'last_sync_at')
    search_fields = ('user__email', 'peloton_user_id')
    readonly_fields = ('created_at', 'updated_at', 'last_sync_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Peloton Account', {
            'fields': ('peloton_user_id', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_sync_at'),
            'classes': ('collapse',)
        }),
    )
