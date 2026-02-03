#!/usr/bin/env python
"""
Debug script to test the workout assignment save functionality
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/opt/projects/pelvicplanner')
django.setup()

from challenges.models import Challenge, ChallengeWorkoutAssignment
from workouts.models import RideDetail
from accounts.models import User
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from challenges.admin_views import admin_assign_workouts

def test_save_functionality():
    print("🔧 Starting workout assignment save debug...")
    
    # Get first challenge for testing
    challenge = Challenge.objects.first()
    if not challenge:
        print("❌ No challenges found - please create a challenge first")
        return
    
    print(f"📋 Testing with challenge: {challenge.name}")
    
    # Get a sample RideDetail for testing
    ride = RideDetail.objects.first()
    if not ride:
        print("❌ No RideDetail objects found - please sync some classes first")
        return
        
    print(f"🚴 Testing with ride: {ride.title}")
    print(f"   - ID: {ride.id}")
    print(f"   - Peloton ID: {ride.peloton_ride_id}")
    print(f"   - Has metrics: {bool(ride.target_metrics_data)}")
    
    # Get admin user
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("⚠️  No admin user found, creating test user...")
        admin_user = User.objects.create_user(
            email='debug@test.com',
            username='debug_admin',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
    print(f"👤 Testing with admin: {admin_user.username}")
    
    # Create a test request
    factory = RequestFactory()
    request = factory.post(f'/challenges/admin/{challenge.id}/assign-workouts/', {
        f'ride_id_{challenge.available_templates.first().id}_1_0_ride': str(ride.id),
        f'workout_{challenge.available_templates.first().id}_1_0_ride': '',
        f'title_{challenge.available_templates.first().id}_1_0_ride': ride.title,
        f'points_{challenge.available_templates.first().id}_1_0_ride': '50',
    })
    
    # Set up request with user and messages
    request.user = admin_user
    setattr(request, 'session', {})
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    print("📝 Simulating POST request...")
    
    try:
        response = admin_assign_workouts(request, challenge.id)
        print(f"✅ Response status code: {response.status_code}")
        
        # Check messages
        message_list = list(messages)
        for message in message_list:
            print(f"💬 Message ({message.level_tag}): {message}")
            
        # Check if assignment was created
        assignment = ChallengeWorkoutAssignment.objects.filter(
            challenge=challenge,
            ride_detail=ride
        ).first()
        
        if assignment:
            print(f"✅ Assignment created successfully:")
            print(f"   - Ride: {assignment.ride_detail.title}")
            print(f"   - URL: {assignment.peloton_url}")
            print(f"   - Points: {assignment.points}")
        else:
            print("❌ No assignment was created")
            
    except Exception as e:
        print(f"❌ Error during save: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_save_functionality()