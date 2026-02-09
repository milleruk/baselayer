from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, datetime, timedelta
from django.utils import timezone

from .models import Challenge, ChallengeInstance, Team, TeamMember
from plans.models import PlanTemplate
from tracker.models import WeeklyPlan, DailyPlanItem

User = get_user_model()


class ChallengeSignupScoringTests(TestCase):
	def setUp(self):
		self.user1 = User.objects.create_user(email='u1@example.com', password='pass')
		self.user2 = User.objects.create_user(email='u2@example.com', password='pass')
		self.template = PlanTemplate.objects.create(name='Test Template')
		# Create a minimal Exercise for DailyPlanItem FK
		from plans.models import Exercise
		self.exercise = Exercise.objects.create(name='Test Exercise', category='yoga', position='', key_cue='', reps_hold='')

	def test_can_signup_respects_deadline_after_start(self):
		today = date.today()
		# Challenge started yesterday but signup deadline is in two days
		chal = Challenge.objects.create(
			name='Deadline Challenge',
			start_date=today - timedelta(days=1),
			end_date=today + timedelta(days=20),
			signup_opens_date=today - timedelta(days=10),
			signup_deadline=today + timedelta(days=2),
			is_active=True,
			is_visible=True,
		)

		self.assertTrue(chal.can_signup)

	def test_challengeinstance_is_scoring_based_on_cutoff(self):
		today = date.today()
		cutoff = today + timedelta(days=2)
		chal = Challenge.objects.create(
			name='Scoring Cutoff',
			start_date=today - timedelta(days=1),
			end_date=today + timedelta(days=20),
			signup_opens_date=today - timedelta(days=10),
			signup_deadline=cutoff,
			is_active=True,
			is_visible=True,
		)

		# Instance joined today -> scoring
		inst1 = ChallengeInstance.objects.create(
			user=self.user1,
			challenge=chal,
			selected_template=self.template,
			is_active=True,
		)
		inst1.started_at = datetime.combine(today, datetime.min.time())
		inst1.save(update_fields=['started_at'])
		self.assertTrue(inst1.is_scoring)

		# Instance joined after cutoff -> non-scoring
		inst2 = ChallengeInstance.objects.create(
			user=self.user2,
			challenge=chal,
			selected_template=self.template,
			is_active=True,
		)
		later = cutoff + timedelta(days=1)
		inst2.started_at = datetime.combine(later, datetime.min.time())
		inst2.save(update_fields=['started_at'])
		self.assertFalse(inst2.is_scoring)

	def test_team_score_excludes_non_scoring_members(self):
		today = date.today()
		cutoff = today + timedelta(days=2)
		chal = Challenge.objects.create(
			name='Team Score',
			start_date=today - timedelta(days=1),
			end_date=today + timedelta(days=20),
			signup_opens_date=today - timedelta(days=10),
			signup_deadline=cutoff,
			challenge_type='team',
			is_active=True,
			is_visible=True,
		)

		team = Team.objects.create(name='Red Team')

		# Scoring member
		inst1 = ChallengeInstance.objects.create(user=self.user1, challenge=chal, selected_template=self.template, is_active=True)
		inst1.started_at = datetime.combine(today, datetime.min.time())
		inst1.save(update_fields=['started_at'])
		TeamMember.objects.create(team=team, challenge_instance=inst1)

		# Non-scoring member (joined after cutoff)
		inst2 = ChallengeInstance.objects.create(user=self.user2, challenge=chal, selected_template=self.template, is_active=True)
		later = cutoff + timedelta(days=1)
		inst2.started_at = datetime.combine(later, datetime.min.time())
		inst2.save(update_fields=['started_at'])
		TeamMember.objects.create(team=team, challenge_instance=inst2)

		# Create weekly plans with points for both instances
		wp1 = WeeklyPlan.objects.create(user=self.user1, challenge_instance=inst1, week_start=today, template_name='T')
		item1 = DailyPlanItem.objects.create(weekly_plan=wp1, day_of_week=0, peloton_focus='Ride', exercise=self.exercise, ride_done=True, workout_points=50)

		wp2 = WeeklyPlan.objects.create(user=self.user2, challenge_instance=inst2, week_start=today, template_name='T')
		item2 = DailyPlanItem.objects.create(weekly_plan=wp2, day_of_week=0, peloton_focus='Ride', exercise=self.exercise, ride_done=True, workout_points=50)

		# Team score should only include inst1's points
		total = team.calculate_team_score(chal)
		self.assertEqual(total, wp1.total_points)
