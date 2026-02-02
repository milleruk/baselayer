"""Challenge-related business logic and operations."""
from typing import Dict, Optional, Any, Tuple
from datetime import date


class ChallengeService:
    """Service for challenge-related operations and queries."""
    
    @staticmethod
    def get_active_challenge(user) -> Optional[Any]:
        """Get user's currently active challenge instance.
        
        Args:
            user: Django User object
            
        Returns:
            ChallengeInstance object if user has an active challenge, None otherwise
            
        Example:
            >>> active = ChallengeService.get_active_challenge(user)
            >>> if active:
            ...     print(f"User is in {active.challenge.name}")
        """
        from challenges.models import ChallengeInstance
        
        return ChallengeInstance.objects.filter(
            user=user,
            is_active=True
        ).select_related('challenge').prefetch_related(
            'weekly_plans', 
            'team_membership__team'
        ).first()
    
    @staticmethod
    def has_current_week_plan(user, week_start: date) -> bool:
        """Check if user has a plan for the specified week.
        
        Args:
            user: Django User object
            week_start: Date of the week start (typically Sunday)
            
        Returns:
            True if user has a WeeklyPlan for this week, False otherwise
            
        Example:
            >>> from core.services import DateRangeService
            >>> week_start = DateRangeService.sunday_of_current_week(date.today())
            >>> has_plan = ChallengeService.has_current_week_plan(user, week_start)
        """
        from tracker.models import WeeklyPlan
        
        return WeeklyPlan.objects.filter(
            user=user,
            week_start=week_start
        ).exists()
    
    @staticmethod
    def get_challenge_involvement_summary(user) -> Dict[str, Any]:
        """Get summary of user's challenge involvement.
        
        Provides a quick overview of user's active and completed challenges.
        
        Args:
            user: Django User object
            
        Returns:
            Dictionary with:
                - active_challenge: Current active ChallengeInstance or None
                - completed_challenges_count: Number of completed challenges
                - has_involvement: Boolean indicating any challenge involvement
                
        Example:
            >>> summary = ChallengeService.get_challenge_involvement_summary(user)
            >>> if summary['has_involvement']:
            ...     if summary['active_challenge']:
            ...         print(f"Active: {summary['active_challenge'].challenge.name}")
            ...     print(f"Completed: {summary['completed_challenges_count']}")
        """
        from challenges.models import ChallengeInstance
        
        # Get active challenge
        active_challenge = ChallengeService.get_active_challenge(user)
        
        # Get all challenge instances for this user
        all_challenge_instances = ChallengeInstance.objects.filter(
            user=user
        ).prefetch_related('weekly_plans')
        
        # Count completed challenges (all weeks completed)
        completed_challenges_count = sum(
            1 for ci in all_challenge_instances
            if ci.all_weeks_completed
        )
        
        return {
            'active_challenge': active_challenge,
            'completed_challenges_count': completed_challenges_count,
            'has_involvement': active_challenge is not None or completed_challenges_count > 0,
        }
    
    @staticmethod
    def can_join_challenge(user, challenge) -> Tuple[bool, Optional[str]]:
        """Check if user can join a challenge.
        
        Validates signup availability and prevents conflicting active challenges.
        
        Args:
            user: Django User object
            challenge: Challenge object
            
        Returns:
            Tuple of (can_join: bool, error_message: Optional[str])
            If can_join is False, error_message explains why
            
        Example:
            >>> can_join, error = ChallengeService.can_join_challenge(user, challenge)
            >>> if not can_join:
            ...     print(f"Cannot join: {error}")
        """
        from challenges.models import ChallengeInstance
        
        # Check if challenge signup is available
        if not challenge.can_signup:
            return False, f"Signup for '{challenge.name}' is not available at this time"
        
        # For active/running challenges: check if user already has an active challenge
        today = date.today()
        if challenge.start_date <= today and today <= challenge.end_date:
            # Challenge is currently running
            active_challenge_instance = ChallengeService.get_active_challenge(user)
            if active_challenge_instance and active_challenge_instance.challenge.id != challenge.id:
                return False, f"You are already actively participating in '{active_challenge_instance.challenge.name}'. Complete or leave that challenge first."
        
        # Check if user already has an active instance for this challenge
        existing_active = ChallengeInstance.objects.filter(
            user=user,
            challenge=challenge,
            is_active=True
        ).first()
        
        if existing_active:
            return False, f"You're already signed up for '{challenge.name}'"
        
        return True, None
    
    @staticmethod
    def get_all_user_challenge_instances(user, include_inactive: bool = False) -> list:
        """Get all challenge instances for a user.
        
        Args:
            user: Django User object
            include_inactive: Whether to include inactive/abandoned instances
            
        Returns:
            List of ChallengeInstance objects, ordered by most recent first
            
        Example:
            >>> instances = ChallengeService.get_all_user_challenge_instances(user)
            >>> for instance in instances:
            ...     print(f"{instance.challenge.name}: {instance.completion_rate}%")
        """
        from challenges.models import ChallengeInstance
        
        query = ChallengeInstance.objects.filter(user=user)
        
        if not include_inactive:
            query = query.filter(is_active=True)
        
        return query.select_related('challenge').prefetch_related(
            'weekly_plans'
        ).order_by('-started_at')
    
    @staticmethod
    def get_user_challenge_with_week_info(user) -> list:
        """Get all user's challenge instances with week number and access info.
        
        Returns challenge instances grouped with their weekly plans, including
        calculated week numbers and access control information.
        
        Args:
            user: Django User object
            
        Returns:
            List of dictionaries with:
                - challenge_instance: ChallengeInstance object
                - challenge: Challenge object (shortcut)
                - plans_with_week_info: List of dicts with plan and week_number
                - can_leave: Whether user can leave this challenge
                - leave_error: Reason if cannot leave (None if can leave)
                
        Example:
            >>> challenge_data = ChallengeService.get_user_challenge_with_week_info(user)
            >>> for data in challenge_data:
            ...     print(data['challenge'].name)
            ...     for plan_info in data['plans_with_week_info']:
            ...         print(f"  Week {plan_info['week_number']}: {plan_info['completion_rate']}%")
        """
        from challenges.models import ChallengeInstance
        
        challenge_instances = ChallengeInstance.objects.filter(
            user=user
        ).select_related('challenge').prefetch_related('weekly_plans').order_by('started_at')
        
        result = []
        
        for ci in challenge_instances:
            plans = ci.weekly_plans.all().order_by('week_start')
            plans_with_week_info = []
            
            for idx, plan in enumerate(plans, start=1):
                plans_with_week_info.append({
                    'plan': plan,
                    'week_number': idx,
                    'is_completed': plan.is_completed,
                    'completion_rate': getattr(plan, 'completion_rate', 0),
                    'total_points': getattr(plan, 'total_points', 0),
                })
            
            can_leave, leave_error = ci.can_leave_challenge()
            
            result.append({
                'challenge_instance': ci,
                'challenge': ci.challenge,
                'plans_with_week_info': plans_with_week_info,
                'can_leave': can_leave,
                'leave_error': leave_error,
                'total_weeks': len(plans_with_week_info),
                'completed_weeks': sum(1 for p in plans_with_week_info if p['is_completed']),
                'is_active': ci.is_active,
                'completion_rate': ci.completion_rate,
                'total_points': ci.total_points,
            })
        
        return result
    
    @staticmethod
    def deactivate_challenge(user, challenge_instance) -> Tuple[bool, Optional[str]]:
        """Deactivate/leave a challenge instance.
        
        Args:
            user: Django User object (for permission check)
            challenge_instance: ChallengeInstance to deactivate
            
        Returns:
            Tuple of (success: bool, message: Optional[str])
            
        Example:
            >>> success, msg = ChallengeService.deactivate_challenge(user, instance)
            >>> if success:
            ...     print("Left challenge successfully")
            >>> else:
            ...     print(f"Cannot leave: {msg}")
        """
        # Verify user owns this challenge instance
        if challenge_instance.user != user:
            return False, "Permission denied"
        
        # Check if can leave
        can_leave, error = challenge_instance.can_leave_challenge()
        if not can_leave:
            return False, error
        
        # Deactivate the instance
        challenge_instance.is_active = False
        challenge_instance.save(update_fields=['is_active'])
        
        return True, "Successfully left the challenge"
    
    @staticmethod
    def get_challenge_stats(challenge_instance) -> Dict[str, Any]:
        """Get comprehensive statistics for a challenge instance.
        
        Args:
            challenge_instance: ChallengeInstance object
            
        Returns:
            Dictionary with various statistics about challenge participation
            
        Example:
            >>> stats = ChallengeService.get_challenge_stats(instance)
            >>> print(f"Points: {stats['total_points']}")
            >>> print(f"Completion: {stats['completion_rate']}%")
            >>> print(f"Weeks done: {stats['weeks_completed']}/{stats['total_weeks']}")
        """
        plans = challenge_instance.weekly_plans.all()
        
        if not plans.exists():
            return {
                'total_weeks': 0,
                'weeks_completed': 0,
                'completion_rate': 0,
                'total_points': 0,
                'is_fully_completed': False,
                'weeks_list': [],
            }
        
        weeks_list = []
        weeks_completed = 0
        total_points = 0
        
        for idx, plan in enumerate(plans.order_by('week_start'), start=1):
            is_completed = plan.is_completed
            if is_completed:
                weeks_completed += 1
            
            total_points += getattr(plan, 'total_points', 0)
            
            weeks_list.append({
                'week_number': idx,
                'week_start': plan.week_start,
                'is_completed': is_completed,
                'points': getattr(plan, 'total_points', 0),
            })
        
        total_weeks = len(weeks_list)
        completion_rate = (weeks_completed / total_weeks * 100) if total_weeks > 0 else 0
        
        return {
            'total_weeks': total_weeks,
            'weeks_completed': weeks_completed,
            'completion_rate': completion_rate,
            'total_points': total_points,
            'is_fully_completed': weeks_completed == total_weeks,
            'weeks_list': weeks_list,
        }
