from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from challenges.models import Challenge, Team, TeamLeaderboard


class Command(BaseCommand):
    help = 'Calculate team leaderboards for all active team challenges (run at midnight BST)'

    def handle(self, *args, **options):
        today = date.today()
        
        # Get all active team challenges
        active_challenges = Challenge.objects.filter(
            challenge_type="team",
            is_active=True
        )
        
        if not active_challenges.exists():
            self.stdout.write(self.style.WARNING('No active team challenges found.'))
            return
        
        total_calculated = 0
        
        for challenge in active_challenges:
            self.stdout.write(f'Calculating leaderboards for: {challenge.name}')
            
            # Get all teams participating in this challenge
            participating_teams = Team.objects.filter(
                members__challenge_instance__challenge=challenge,
                members__challenge_instance__is_active=True
            ).distinct()
            
            if not participating_teams.exists():
                self.stdout.write(self.style.WARNING(f'  No teams found for {challenge.name}'))
                continue
            
            # Calculate total scores (week_number=None)
            for team in participating_teams:
                score = team.calculate_team_score(challenge, week_number=None)
                entry = team.get_leaderboard_entry(challenge, week_number=None)
                entry.total_points = score
                entry.save()
                total_calculated += 1
            
            # Calculate scores for each week
            for week_num in challenge.week_range:
                # Only calculate for weeks that have started
                week_start = challenge.start_date + timedelta(days=(week_num - 1) * 7)
                if week_start <= today:
                    for team in participating_teams:
                        score = team.calculate_team_score(challenge, week_number=week_num)
                        entry = team.get_leaderboard_entry(challenge, week_number=week_num)
                        entry.total_points = score
                        entry.save()
                        total_calculated += 1
            
            self.stdout.write(self.style.SUCCESS(f'  Calculated scores for {participating_teams.count()} teams'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully calculated {total_calculated} leaderboard entries across {active_challenges.count()} challenges.'
            )
        )
