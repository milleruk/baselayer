from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from plans.models import PlanTemplate
from tracker.models import DailyPlanItem

class Challenge(models.Model):
    """Admin-defined challenge with time periods and workout configuration"""
    CHALLENGE_TYPE_CHOICES = [
        ("team", "Team Challenge"),
        ("mini", "Mini Challenge"),
        ("individual", "Individual Challenge"),
    ]
    
    CATEGORY_CHOICES = [
        ("cycling", "CYCLING"),
        ("running", "RUNNING"),
        ("strength", "STRENGTH"),
        ("yoga", "YOGA"),
    ]
    
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    start_date = models.DateField(help_text="Challenge start date")
    end_date = models.DateField(help_text="Challenge end date")
    signup_opens_date = models.DateField(null=True, blank=True, help_text="Date when signup opens for this challenge (optional, defaults to challenge start date)")
    signup_deadline = models.DateField(null=True, blank=True, help_text="Last date users can sign up (optional)")
    is_active = models.BooleanField(default=True, help_text="Whether this challenge is currently active")
    is_visible = models.BooleanField(default=True, help_text="Whether this challenge is visible for signup")
    team_leaders_can_see_users = models.BooleanField(default=False, help_text="Whether team leaders can see the user list (only after challenge starts)")
    team_leaders_see_users_date = models.DateField(null=True, blank=True, help_text="Date when team leaders can see the user list (optional, defaults to challenge start date)")
    challenge_type = models.CharField(max_length=20, choices=CHALLENGE_TYPE_CHOICES, default="mini")
    categories = models.CharField(max_length=200, blank=True, default="", help_text="Comma-separated categories (cycling,running,strength,yoga)")
    image = models.ImageField(upload_to="challenges/", blank=True, null=True, help_text="Challenge logo/image")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Workout configuration - which templates are available for this challenge
    available_templates = models.ManyToManyField(
        PlanTemplate,
        related_name="challenges",
        db_table="tracker_challenge_available_templates",
        help_text="Plan templates available for this challenge. Users can choose from these when joining."
    )
    # Default/recommended template (should be one of the available templates)
    default_template = models.ForeignKey(PlanTemplate, on_delete=models.SET_NULL, null=True, blank=True, 
                                         help_text="Recommended template (should be one of the available templates)")
    
    def get_categories_list(self):
        """Return categories as a list"""
        if not self.categories:
            return []
        return [cat.strip().upper() for cat in self.categories.split(",")]
    
    class Meta:
        db_table = "tracker_challenge"
        managed = False
        ordering = ["start_date", "created_at"]  # Earliest first
    
    def __str__(self):
        return self.name
    
    @property
    def is_currently_running(self):
        """Check if challenge is currently running"""
        today = date.today()
        return self.start_date <= today <= self.end_date
    
    @property
    def has_ended(self):
        """Check if challenge has ended"""
        return date.today() > self.end_date
    
    @property
    def can_signup(self):
        """Check if users can still sign up - based on signup_opens_date, signup_deadline, and challenge status"""
        if not self.is_visible:
            return False
        
        today = date.today()
        
        # Can always retake past challenges (after they've ended)
        if self.has_ended:
            return True
        
        # Cannot join once challenge has started (but hasn't ended yet)
        if today >= self.start_date:
            return False
        
        # Check if signup has opened yet
        signup_opens = self.signup_opens_date if self.signup_opens_date else self.start_date
        if today < signup_opens:
            return False  # Signup hasn't opened yet
        
        # Check signup deadline if set
        if self.signup_deadline:
            return today <= self.signup_deadline
        
        # If no deadline, can signup after signup opens and before challenge starts
        return True
    
    def team_leaders_can_see_user_list(self):
        """Check if team leaders can see the user list for this challenge"""
        if not self.team_leaders_can_see_users:
            return False
        
        today = date.today()
        
        # If specific visibility date is set, use that (can be before challenge starts)
        if self.team_leaders_see_users_date:
            return today >= self.team_leaders_see_users_date
        
        # Default to challenge start date (must be after challenge starts)
        return today >= self.start_date
    
    @property
    def duration_weeks(self):
        """Calculate duration in weeks"""
        if not self.start_date or not self.end_date:
            return 0
        delta = self.end_date - self.start_date
        return max(1, (delta.days // 7) + 1)
    
    @property
    def week_range(self):
        """Return a range of week numbers for this challenge"""
        return range(1, self.duration_weeks + 1)
    
    def is_week_unlocked(self, week_number):
        """Check if a specific week is unlocked/live"""
        # If challenge has ended, all weeks are unlocked (for retaking past challenges)
        if self.has_ended:
            return True
        
        # For active/upcoming challenges, check unlock status
        try:
            unlock = self.week_unlocks.get(week_number=week_number)
            # Check if manually unlocked
            if unlock.is_unlocked:
                return True
            # Check if auto-unlock date has passed
            if unlock.unlock_date and date.today() >= unlock.unlock_date:
                # Auto-unlock it
                unlock.is_unlocked = True
                unlock.save()
                return True
            return False
        except ChallengeWeekUnlock.DoesNotExist:
            # If no unlock record exists, check if challenge has started
            # If challenge hasn't started yet, lock all weeks
            if date.today() < self.start_date:
                return False
            # If challenge has started but no unlock record, unlock week 1 by default
            # Other weeks need explicit unlock
            return week_number == 1
    
    def get_unlocked_weeks(self):
        """Get list of unlocked week numbers"""
        unlocked = []
        for week_num in self.week_range:
            if self.is_week_unlocked(week_num):
                unlocked.append(week_num)
        return unlocked
    
    def get_scoring_participants(self):
        """Get challenge instances that are contributing to team scores"""
        if self.challenge_type != "team":
            return self.instances.all()
        
        # For team challenges, filter to only scoring participants
        return [instance for instance in self.instances.all() if instance.is_scoring]
    
    def get_team_total_points(self):
        """Get total points from all scoring participants (for team challenges)"""
        if self.challenge_type != "team":
            return None
        
        scoring_instances = self.get_scoring_participants()
        return sum(instance.total_points for instance in scoring_instances)
    
    def clean(self):
        """Validate challenge dates"""
        # Validate that end_date is after start_date
        if self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End date must be after start date.'
            })
        
        # Validate that signup_deadline is before start_date if set
        if self.signup_deadline and self.signup_deadline >= self.start_date:
            raise ValidationError({
                'signup_deadline': 'Signup deadline must be before the challenge start date.'
            })
        
        # Note: Overlapping challenges are now allowed
        # Users can sign up for multiple future challenges, but can only actively participate in one at a time
    
    def save(self, *args, **kwargs):
        """Override save to call clean() validation"""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # After saving, validate that default_template is in available_templates
        # This needs to happen after save because ManyToMany fields need the object to be saved first
        if self.default_template and self.available_templates.exists():
            if self.default_template not in self.available_templates.all():
                # Clear default_template if it's not in available_templates
                self.default_template = None
                super().save(update_fields=['default_template'])


class ChallengeInstance(models.Model):
    """User's participation in a challenge"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenge_instances")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="instances")
    selected_template = models.ForeignKey(PlanTemplate, on_delete=models.SET_NULL, null=True, blank=True,
                                         help_text="User's chosen plan template for this challenge")
    include_kegels = models.BooleanField(default=True, help_text="Whether user wants to include Kegel exercises in their plan")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "tracker_challengeinstance"
        managed = False
        # Removed unique_together to allow multiple attempts per challenge
        ordering = ["-started_at"]
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.name}"
    
    @property
    def total_points(self):
        return sum(plan.total_points for plan in self.weekly_plans.all())
    
    @property
    def completion_rate(self):
        plans = self.weekly_plans.all()
        if not plans:
            return 0
        completed = sum(1 for plan in plans if plan.is_completed)
        return (completed / len(plans)) * 100
    
    @property
    def all_weeks_completed(self):
        """Check if all weeks in this challenge are completed"""
        plans = self.weekly_plans.all()
        if not plans:
            return False
        return all(plan.is_completed for plan in plans)
    
    def can_leave_challenge(self):
        """
        Check if user can leave this challenge.
        - Past challenges: Always can leave
        - Live challenges: Can only leave if they haven't completed anything in the previous week
        """
        # Past challenges: always can leave
        if self.challenge.has_ended:
            return True, None
        
        # Live challenges: check previous week completion
        if self.challenge.is_currently_running:
            plans = self.weekly_plans.all().order_by("week_start")
            if not plans.exists():
                # No plans yet, can leave
                return True, None
            
            # Find current week number based on today's date
            from datetime import date, timedelta
            today = date.today()
            challenge_start = self.challenge.start_date
            
            # Calculate which week we're currently in
            days_since_start = (today - challenge_start).days
            current_week_num = (days_since_start // 7) + 1
            
            # If we're in week 1, can always leave (no previous week)
            if current_week_num <= 1:
                return True, None
            
            # Check previous week (current_week_num - 1)
            previous_week_num = current_week_num - 1
            
            # Find the plan for the previous week
            previous_week_start = challenge_start + timedelta(days=(previous_week_num - 1) * 7)
            previous_plan = plans.filter(week_start=previous_week_start).first()
            
            if not previous_plan:
                # Previous week plan doesn't exist, can leave
                return True, None
            
            # Check if user has completed ANY activities in the previous week
            # Check for completed exercises
            has_completed_exercises = previous_plan.items.filter(is_done=True).exists()
            
            # Check for completed Peloton activities
            has_completed_activities = (
                previous_plan.items.filter(ride_done=True).exists() or
                previous_plan.items.filter(run_done=True).exists() or
                previous_plan.items.filter(yoga_done=True).exists() or
                previous_plan.items.filter(strength_done=True).exists()
            )
            
            # Check for completed bonus workout
            has_completed_bonus = previous_plan.bonus_workout_done
            
            # If they've completed anything in previous week, can't leave
            if has_completed_exercises or has_completed_activities or has_completed_bonus:
                return False, f"You cannot leave this challenge because you've completed activities in Week {previous_week_num}. You can leave if you don't complete anything in Week {current_week_num}."
            
            # No completions in previous week, can leave
            return True, None
        
        # Upcoming challenges: can leave
        return True, None
    
    @property
    def is_scoring(self):
        """
        Check if this user is contributing to team scores.
        For active challenges, users must be completing activities to score.
        For past challenges, all participants score.
        """
        # If challenge has ended, user always scores (for historical purposes)
        if self.challenge.has_ended:
            return True
        
        # If challenge hasn't started yet, user scores (they're signed up)
        if date.today() < self.challenge.start_date:
            return True
        
        # For active challenges, check if user is completing activities
        if self.challenge.is_currently_running:
            # Get all plans for this challenge instance
            plans = self.weekly_plans.all().order_by("week_start")
            if not plans.exists():
                # No plans yet, but challenge is running - don't score until they start
                return False
            
            # Check if user has completed any activities in the last 2 weeks
            # This ensures they're actively participating
            today = date.today()
            two_weeks_ago = today - timedelta(days=14)
            
            # Get plans from the last 2 weeks
            recent_plans = plans.filter(week_start__gte=two_weeks_ago)
            
            if recent_plans.exists():
                # Check if any recent plan has completed activities
                for plan in recent_plans:
                    # Check if plan has any completed exercises or activities
                    items = plan.items.all()
                    for item in items:
                        # Check if any exercise is done (kegel exercises)
                        if item.is_done:
                            return True
                        # Check if any Peloton activity is done
                        if (item.peloton_ride_url and item.ride_done) or \
                           (item.peloton_run_url and item.run_done) or \
                           (item.peloton_yoga_url and item.yoga_done) or \
                           (item.peloton_strength_url and item.strength_done):
                            return True
                
                # No activities completed in recent weeks - not scoring
                return False
            else:
                # No recent plans, but challenge is running - check if they have any plans at all
                # If they have plans but none are recent, they might have joined early
                # Check if they've completed anything ever
                for plan in plans:
                    items = plan.items.all()
                    for item in items:
                        if item.is_done or item.ride_done or item.run_done or item.yoga_done or item.strength_done:
                            return True
                return False
        
        # For upcoming challenges, user scores (they're signed up)
        return True
    
    @property
    def contributes_to_team_score(self):
        """Alias for is_scoring - for team challenge compatibility"""
        return self.is_scoring
    
    @property
    def is_first_completion(self):
        """Check if this is the first completed instance of this challenge for the user"""
        if not self.completed_at:
            return False
        # Get all completed instances for this user and challenge, ordered by completion date
        completed_instances = ChallengeInstance.objects.filter(
            user=self.user,
            challenge=self.challenge,
            completed_at__isnull=False
        ).order_by('completed_at')
        # Check if this is the first one
        return completed_instances.exists() and completed_instances.first().id == self.id
    
    @classmethod
    def get_retake_count(cls, user, challenge):
        """Get how many times a user has taken a challenge"""
        return cls.objects.filter(user=user, challenge=challenge).count()
    
    def has_conflicting_active_challenge(self, user):
        """
        Check if user has another active challenge that conflicts with this one.
        Returns (has_conflict, conflicting_instance) tuple.
        """
        from datetime import date
        today = date.today()
        
        # Only check for conflicts if this challenge has started
        if self.start_date > today:
            return False, None
        
        # Find other active challenges that are currently running
        other_active = ChallengeInstance.objects.filter(
            user=user,
            is_active=True
        ).exclude(
            challenge=self
        ).select_related('challenge')
        
        for instance in other_active:
            # Check if the other challenge is currently running (overlaps with this one)
            other_challenge = instance.challenge
            if other_challenge.is_currently_running:
                # Check if date ranges overlap
                if (self.start_date <= other_challenge.end_date and 
                    self.end_date >= other_challenge.start_date):
                    return True, instance
        
        return False, None


class ChallengeWorkoutAssignment(models.Model):
    """Stores Peloton workout assignments for challenge templates"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="workout_assignments")
    template = models.ForeignKey(PlanTemplate, on_delete=models.CASCADE, related_name="workout_assignments")
    week_number = models.IntegerField(help_text="Week number (1-based)")
    day_of_week = models.IntegerField(choices=DailyPlanItem.DAY_CHOICES, help_text="Day of week")
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ("ride", "Ride"),
            ("run", "Run"),
            ("yoga", "Yoga"),
            ("strength", "Strength"),
        ],
        help_text="Type of activity"
    )
    peloton_url = models.URLField(help_text="Peloton workout URL")
    workout_title = models.CharField(max_length=200, blank=True, help_text="Optional: Workout title/description")
    points = models.IntegerField(default=50, help_text="Points awarded for completing this workout")
    alternative_group = models.IntegerField(null=True, blank=True, help_text="Group ID for alternative workouts (same group = user chooses one)")
    order_in_group = models.IntegerField(default=0, help_text="Order within alternative group")
    
    class Meta:
        db_table = "tracker_challengeworkoutassignment"
        managed = False
        unique_together = ("challenge", "template", "week_number", "day_of_week", "activity_type", "alternative_group", "order_in_group")
        ordering = ["challenge", "template", "week_number", "day_of_week", "activity_type", "alternative_group", "order_in_group"]
    
    def __str__(self):
        return f"{self.challenge.name} - {self.template.name} - Week {self.week_number} - {self.get_day_of_week_display()} - {self.get_activity_type_display()}"


class ChallengeBonusWorkout(models.Model):
    """Stores bonus workout assignments for challenges (same for all templates)"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="bonus_workouts")
    week_number = models.IntegerField(help_text="Week number (1-based)")
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ("ride", "Ride"),
            ("run", "Run"),
            ("yoga", "Yoga"),
            ("strength", "Strength"),
        ],
        help_text="Type of activity"
    )
    peloton_url = models.URLField(blank=True, help_text="Peloton workout URL (leave empty for 'Any 30 min+ Peloton Workout')")
    workout_title = models.CharField(max_length=200, blank=True, help_text="Optional: Workout title/description")
    points = models.IntegerField(default=10, help_text="Points awarded for completing this bonus workout")
    
    class Meta:
        db_table = "tracker_challengebonusworkout"
        managed = False
        unique_together = ("challenge", "week_number")
        ordering = ["challenge", "week_number"]
    
    def __str__(self):
        return f"{self.challenge.name} - Week {self.week_number} - {self.get_activity_type_display()} (Bonus)"


class ChallengeWeekUnlock(models.Model):
    """Tracks which weeks are unlocked/live for a challenge"""
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="week_unlocks")
    week_number = models.IntegerField(help_text="Week number (1-based)")
    is_unlocked = models.BooleanField(default=False, help_text="Whether this week is currently unlocked/live")
    unlock_date = models.DateField(null=True, blank=True, help_text="Optional: Date when this week should automatically unlock")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "tracker_challengeweekunlock"
        managed = False
        unique_together = ("challenge", "week_number")
        ordering = ["challenge", "week_number"]
    
    def __str__(self):
        status = "Unlocked" if self.is_unlocked else "Locked"
        return f"{self.challenge.name} - Week {self.week_number} ({status})"


class Team(models.Model):
    """Team for challenges - teams persist across challenges with static team leaders.
    Maximum of 3 team leaders per team."""
    name = models.CharField(max_length=120, unique=True, help_text="Team name")
    leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name="led_teams", help_text="Primary team leader (static across all challenges)")
    max_members = models.IntegerField(default=999999, help_text="Maximum number of members per team (effectively unlimited)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def team_leaders(self):
        """Get all team leaders for this team (max 3)"""
        leaders = []
        if self.leader:
            leaders.append(self.leader)
        # Get additional leaders from TeamLeader model if we add it, or from a many-to-many
        # For now, just return the primary leader
        return leaders[:3]
    
    def can_add_leader(self):
        """Check if team can add another leader (max 3)"""
        return len(self.team_leaders) < 3
    
    class Meta:
        db_table = "challenges_team"
        ordering = ["name"]
    
    def __str__(self):
        return self.name
    
    @property
    def current_member_count(self):
        """Get current number of active members across all challenges"""
        return self.members.filter(challenge_instance__is_active=True).count()
    
    def get_members_for_challenge(self, challenge):
        """Get all team members for a specific challenge"""
        return self.members.filter(challenge_instance__challenge=challenge, challenge_instance__is_active=True)
    
    def can_join(self, challenge):
        """Check if team can accept new members for a challenge (unlimited members)"""
        return True  # No limit on team size
    
    def calculate_team_score(self, challenge, week_number=None):
        """Calculate total team score for a challenge (optionally for a specific week)"""
        members = self.get_members_for_challenge(challenge)
        total_score = 0
        
        for member in members:
            instance = member.challenge_instance
            if not instance.is_scoring:
                continue
            
            if week_number:
                # Calculate score for specific week
                from tracker.models import WeeklyPlan
                from datetime import timedelta
                challenge_start = challenge.start_date
                week_start = challenge_start + timedelta(days=(week_number - 1) * 7)
                week_plan = instance.weekly_plans.filter(week_start=week_start).first()
                if week_plan:
                    total_score += week_plan.total_points
            else:
                # Calculate total score across all weeks
                total_score += instance.total_points
        
        return total_score
    
    def get_leaderboard_entry(self, challenge, week_number=None):
        """Get or create leaderboard entry for this team/challenge/week"""
        entry, created = TeamLeaderboard.objects.get_or_create(
            team=self,
            challenge=challenge,
            week_number=week_number,
            defaults={'total_points': 0}
        )
        return entry


class TeamMember(models.Model):
    """Tracks which users are in which teams for which challenges"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    challenge_instance = models.OneToOneField(ChallengeInstance, on_delete=models.CASCADE, 
                                            related_name="team_membership", 
                                            help_text="User's participation in a challenge")
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "challenges_teammember"
        unique_together = ("team", "challenge_instance")
        ordering = ["-joined_at"]
    
    def __str__(self):
        return f"{self.challenge_instance.user.email} - {self.team.name} ({self.challenge_instance.challenge.name})"


class TeamLeaderVolunteer(models.Model):
    """Tracks users who volunteered to be team leaders"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_leader_volunteers")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="team_leader_volunteers")
    challenge_instance = models.ForeignKey(ChallengeInstance, on_delete=models.CASCADE, related_name="team_leader_volunteer",
                                          null=True, blank=True, help_text="Challenge instance when user volunteered")
    volunteered_at = models.DateTimeField(auto_now_add=True)
    assigned = models.BooleanField(default=False, help_text="Whether admin has assigned this volunteer to a team")
    assigned_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name="assigned_volunteers",
                                     help_text="Team this volunteer was assigned to lead")
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "challenges_teamleadervolunteer"
        unique_together = ("user", "challenge")
        ordering = ["-volunteered_at"]
    
    def __str__(self):
        status = "Assigned" if self.assigned else "Pending"
        return f"{self.user.email} - {self.challenge.name} ({status})"


class TeamLeaderboard(models.Model):
    """Stores calculated team scores for leaderboards (calculated at midnight BST)"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="leaderboard_entries")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="team_leaderboards")
    week_number = models.IntegerField(null=True, blank=True, help_text="Week number (null = total score)")
    total_points = models.IntegerField(default=0, help_text="Total team points for this challenge/week")
    calculated_at = models.DateTimeField(auto_now_add=True, help_text="When this score was calculated")
    
    class Meta:
        db_table = "challenges_teamleaderboard"
        unique_together = ("team", "challenge", "week_number")
        ordering = ["-total_points", "team__name"]
        indexes = [
            models.Index(fields=["challenge", "week_number", "-total_points"]),
        ]
    
    def __str__(self):
        week_str = f"Week {self.week_number}" if self.week_number else "Total"
        return f"{self.team.name} - {self.challenge.name} - {week_str}: {self.total_points} points"
