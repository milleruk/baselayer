from django.urls import path
from . import views

app_name = 'peloton'

urlpatterns = [
    path('connect/', views.connect_peloton, name='connect'),
    path('connect/oauth/', views.start_oauth_flow, name='start_oauth'),
    path('connect/callback/', views.oauth_callback, name='oauth_callback'),
    path('status/', views.peloton_status, name='status'),
    path('grab-followers/', views.grab_followers, name='grab_followers'),
    path('disconnect/', views.disconnect_peloton, name='disconnect'),
    path('test/', views.test_connection, name='test'),
]
