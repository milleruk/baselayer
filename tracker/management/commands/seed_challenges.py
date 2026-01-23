from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from tracker.models import Challenge, ChallengeWorkoutAssignment, ChallengeBonusWorkout
from plans.models import PlanTemplate, PlanTemplateDay
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import io

CHALLENGES = [
    {
        "name": "Foundation Builder",
        "description": "Build your base with three rides a week. Perfect for establishing consistency and developing aerobic capacity.",
        "challenge_type": "team",
        "categories": "cycling",
        "start_date": date.today() + timedelta(days=7),  # Starts in 1 week
        "end_date": date.today() + timedelta(days=35),  # Ends in 5 weeks
        "signup_opens_date": date.today() - timedelta(days=7),  # Signup opened 1 week ago
        "signup_deadline": date.today() + timedelta(days=5),  # Signup closes 5 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/4ECDC4/FFFFFF?text=FOUNDATION+BUILDER",
    },
    {
        "name": "Power Base",
        "description": "Build power and pelvic floor strength with four rides a week. For athletes ready to push their limits.",
        "challenge_type": "mini",
        "categories": "cycling,strength",
        "start_date": date.today() + timedelta(days=42),  # Starts in 6 weeks (after Foundation Builder ends)
        "end_date": date.today() + timedelta(days=70),  # Ends in 10 weeks
        "signup_opens_date": date.today() + timedelta(days=28),  # Signup opens 2 weeks before start
        "signup_deadline": date.today() + timedelta(days=40),  # Signup closes 2 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/FF6B6B/FFFFFF?text=POWER+BASE",
    },
    {
        "name": "Flex Flow",
        "description": "Find your flow and flexibility. Three runs a week combined with yoga for the ultimate mind-body connection.",
        "challenge_type": "mini",
        "categories": "running,yoga",
        "start_date": date.today() - timedelta(days=42),  # Started 6 weeks ago (past challenge)
        "end_date": date.today() - timedelta(days=14),  # Ended 2 weeks ago
        "signup_opens_date": date.today() - timedelta(days=56),  # Signup opened 8 weeks ago
        "signup_deadline": date.today() - timedelta(days=44),  # Signup closed 2 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/9370DB/FFFFFF?text=FLEX+FLOW",
    },
    {
        "name": "Dual Zone Challenge",
        "description": "The ultimate multi-sport challenge. Cycling and running combined for maximum intensity and performance.",
        "challenge_type": "team",
        "categories": "cycling,running",
        "start_date": date.today() + timedelta(days=77),  # Starts in 11 weeks (after Power Base ends)
        "end_date": date.today() + timedelta(days=105),  # Ends in 15 weeks
        "signup_opens_date": date.today() + timedelta(days=63),  # Signup opens 2 weeks before start
        "signup_deadline": date.today() + timedelta(days=75),  # Signup closes 2 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/FF8C00/000000?text=DUAL+ZONE",
    },
    {
        "name": "Strength Foundation",
        "description": "Build strength from the ground up. Strength training combined with pelvic floor exercises for complete power.",
        "challenge_type": "mini",
        "categories": "strength",
        "start_date": date.today() - timedelta(days=70),  # Started 10 weeks ago (past challenge)
        "end_date": date.today() - timedelta(days=49),  # Ended 7 weeks ago
        "signup_opens_date": date.today() - timedelta(days=84),  # Signup opened 12 weeks ago
        "signup_deadline": date.today() - timedelta(days=72),  # Signup closed 2 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/8B0000/FFFFFF?text=STRENGTH+BASE",
    },
    {
        "name": "Mindful Movement",
        "description": "Find balance through yoga and pelvic floor health. Build flexibility, strength, and control.",
        "challenge_type": "mini",
        "categories": "yoga",
        "start_date": date.today() - timedelta(days=98),  # Started 14 weeks ago (past challenge, before Strength Foundation)
        "end_date": date.today() - timedelta(days=77),  # Ended 11 weeks ago (before Strength Foundation starts)
        "signup_opens_date": date.today() - timedelta(days=112),  # Signup opened 16 weeks ago
        "signup_deadline": date.today() - timedelta(days=100),  # Signup closed 2 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/4ECDC4/FFFFFF?text=MINDFUL+MOVEMENT",
    },
    {
        "name": "Complete Base",
        "description": "The comprehensive challenge - cycling, running, strength, and yoga. For committed athletes who want it all.",
        "challenge_type": "team",
        "categories": "cycling,running,strength,yoga",
        "start_date": date.today() - timedelta(days=126),  # Started 18 weeks ago (past challenge, before Mindful Movement)
        "end_date": date.today() - timedelta(days=105),  # Ended 15 weeks ago (before Mindful Movement starts)
        "signup_opens_date": date.today() - timedelta(days=140),  # Signup opened 20 weeks ago
        "signup_deadline": date.today() - timedelta(days=128),  # Signup closed 2 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/FF4500/FFFFFF?text=COMPLETE+BASE",
    },
    {
        "name": "Balanced Base",
        "description": "Balanced training with two runs and two rides per week. Perfect for multi-sport athletes who do it all.",
        "challenge_type": "mini",
        "categories": "running,cycling",
        "start_date": date.today() + timedelta(days=112),  # Starts in 16 weeks (after Dual Zone Challenge ends)
        "end_date": date.today() + timedelta(days=140),  # Ends in 20 weeks
        "signup_opens_date": date.today() + timedelta(days=98),  # Signup opens 2 weeks before start
        "signup_deadline": date.today() + timedelta(days=110),  # Signup closes 2 days before start
        "is_active": True,
        "image_url": "https://via.placeholder.com/400x300/FFD700/000000?text=BALANCED+BASE",
    },
]

class Command(BaseCommand):
    help = "Seeds challenges with funky names and badge-style images."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing challenges first.")
    
    def _lighten_color(self, hex_color):
        """Lighten a hex color for highlight effect"""
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # Lighten by 20%
            r = min(255, int(r * 1.2))
            g = min(255, int(g * 1.2))
            b = min(255, int(b * 1.2))
            return f"#{r:02X}{g:02X}{b:02X}"
        except:
            return f"#{hex_color}"
    
    def _create_workout_assignments(self, challenge):
        """Create Peloton workout assignments for all templates and weeks"""
        num_weeks = challenge.duration_weeks
        templates = challenge.available_templates.all()
        
        # Generate unique Peloton URLs for testing
        # Create unique IDs based on challenge, template, week, day, and activity
        def get_unique_url(activity_type, challenge_id, template_id, week_num, day_num):
            base_urls = {
                "ride": "https://www.onepeloton.com/classes/cycling?classId=",
                "run": "https://www.onepeloton.com/classes/treadmill?classId=",
                "yoga": "https://www.onepeloton.com/classes/yoga?classId=",
                "strength": "https://www.onepeloton.com/classes/strength?classId=",
            }
            activity_offsets = {"ride": 1, "run": 2, "yoga": 3, "strength": 4}
            # Create unique ID: challenge_id * 100000 + template_id * 10000 + week * 1000 + day * 100 + activity_offset
            unique_id = (challenge_id * 100000) + (template_id * 10000) + (week_num * 1000) + (day_num * 100) + activity_offsets.get(activity_type, 0)
            return f"{base_urls[activity_type]}{unique_id}"
        
        assignments_created = 0
        
        for template in templates:
            template_days = {d.day_of_week: d for d in template.days.all()}
            
            for week_num in range(1, num_weeks + 1):
                for day_num in range(7):
                    template_day = template_days.get(day_num)
                    if not template_day:
                        continue
                    
                    focus_lower = template_day.peloton_focus.lower()
                    
                    # Determine which activities are expected for this day
                    has_ride = "pze" in focus_lower or "power zone" in focus_lower or "pz" in focus_lower or ("ride" in focus_lower and "run" not in focus_lower)
                    has_run = "run" in focus_lower
                    has_yoga = "yoga" in focus_lower
                    has_strength = "strength" in focus_lower
                    
                    # Determine workout day number (for alternatives)
                    workout_days = []
                    for d in range(7):
                        td = template_days.get(d)
                        if td:
                            focus_lower_check = td.peloton_focus.lower()
                            if ("pze" in focus_lower_check or "power zone" in focus_lower_check or "pz" in focus_lower_check or 
                                "ride" in focus_lower_check or "run" in focus_lower_check or 
                                "yoga" in focus_lower_check or "strength" in focus_lower_check):
                                workout_days.append(d)
                    
                    workout_day_number = None
                    if day_num in workout_days:
                        workout_day_number = workout_days.index(day_num) + 1
                    
                    # Determine if this day allows alternatives
                    template_name_lower = template.name.lower()
                    is_3_plan = "3" in template_name_lower and ("ride" in template_name_lower or "run" in template_name_lower)
                    is_4_plan = "4" in template_name_lower and ("ride" in template_name_lower or "run" in template_name_lower)
                    is_2r2r_plan = "2 runs 2 rides" in template_name_lower or "2 rides 2 runs" in template_name_lower
                    
                    allows_alternatives = False
                    if is_3_plan and workout_day_number in [2, 3]:  # Day 2 and Day 3 (2nd and 3rd workout days)
                        allows_alternatives = True
                    elif is_4_plan and workout_day_number in [1, 4, 6]:
                        allows_alternatives = True
                    elif is_2r2r_plan and workout_day_number in [2, 4]:  # Day 2 and Day 4 (2nd and 4th workout days)
                        allows_alternatives = True
                    
                    # Assign workouts for each activity type
                    for activity_type, has_activity in [
                        ("ride", has_ride),
                        ("run", has_run),
                        ("yoga", has_yoga),
                        ("strength", has_strength),
                    ]:
                        if has_activity:
                            # Calculate points based on plan type and workout day number
                            # 3-ride/run plans: All workouts = 50 points
                            # 4-ride/run plans: Day 1 = 50, Day 2 = 25, Day 3 = 25, Day 4 = 50
                            # 2 Runs 2 Rides: Day 1 = 50, Day 2 = 25, Day 3 = 25, Day 4 = 50
                            points = 50  # Default
                            if workout_day_number:
                                num_workout_days = len(workout_days)
                                if num_workout_days == 3:
                                    points = 50  # All workouts are 50 points
                                elif num_workout_days == 4:
                                    if workout_day_number == 1 or workout_day_number == 4:
                                        points = 50  # First and last day
                                    else:
                                        points = 25  # Middle days (2 and 3)
                                # For other plans, default to 50
                            
                            # Generate unique URL for primary assignment
                            peloton_url = get_unique_url(activity_type, challenge.id, template.id, week_num, day_num)
                            
                            # Create primary assignment
                            ChallengeWorkoutAssignment.objects.update_or_create(
                                challenge=challenge,
                                template=template,
                                week_number=week_num,
                                day_of_week=day_num,
                                activity_type=activity_type,
                                alternative_group=None,
                                order_in_group=0,
                                defaults={
                                    "peloton_url": peloton_url,
                                    "workout_title": f"Week {week_num} - Day {workout_day_number} {activity_type.title()}",
                                    "points": points,
                                }
                            )
                            assignments_created += 1
                            
                            # Add alternative workout for testing (if this day allows alternatives)
                            if allows_alternatives:
                                # Generate alternative URL (different ID)
                                alt_url = get_unique_url(activity_type, challenge.id, template.id, week_num, day_num + 100)  # Offset by 100 to make unique
                                
                                ChallengeWorkoutAssignment.objects.update_or_create(
                                    challenge=challenge,
                                    template=template,
                                    week_number=week_num,
                                    day_of_week=day_num,
                                    activity_type=activity_type,
                                    alternative_group=day_num,  # Use day_num as group ID
                                    order_in_group=1,
                                    defaults={
                                        "peloton_url": alt_url,
                                        "workout_title": f"Week {week_num} - Day {workout_day_number} {activity_type.title()} (Alternative)",
                                        "points": points,  # Same points as primary
                                    }
                                )
                                assignments_created += 1
        
        if assignments_created > 0:
            self.stdout.write(f"  ✓ Created {assignments_created} Peloton workout assignments")
    
    def _create_bonus_workouts(self, challenge):
        """Create bonus workouts for all weeks of the challenge - one per week"""
        num_weeks = challenge.duration_weeks
        bonus_created = 0
        
        # Determine activity type: run for "3 Runs a Week" challenges, ride for everything else
        challenge_name_lower = challenge.name.lower()
        activity_type = "run" if "3 runs" in challenge_name_lower or ("run" in challenge_name_lower and "3" in challenge_name_lower) else "ride"
        
        # Generate unique Peloton URLs for bonus workouts
        def get_bonus_url(activity_type, challenge_id, week_num):
            base_urls = {
                "ride": "https://www.onepeloton.com/classes/cycling?classId=",
                "run": "https://www.onepeloton.com/classes/treadmill?classId=",
                "yoga": "https://www.onepeloton.com/classes/yoga?classId=",
                "strength": "https://www.onepeloton.com/classes/strength?classId=",
            }
            activity_offsets = {"ride": 1, "run": 2, "yoga": 3, "strength": 4}
            # Create unique ID: challenge_id * 1000000 + week * 10000 + activity_offset + 9000 (bonus offset)
            unique_id = (challenge_id * 1000000) + (week_num * 10000) + activity_offsets.get(activity_type, 0) + 9000
            return f"{base_urls[activity_type]}{unique_id}"
        
        # Create one bonus workout per week (same activity type for all weeks)
        for week_num in range(1, num_weeks + 1):
            peloton_url = get_bonus_url(activity_type, challenge.id, week_num)
            workout_title = f"Week {week_num} Bonus {activity_type.title()}"
            
            ChallengeBonusWorkout.objects.update_or_create(
                challenge=challenge,
                week_number=week_num,
                defaults={
                    "activity_type": activity_type,
                    "peloton_url": peloton_url,
                    "workout_title": workout_title,
                    "points": 10,  # Bonus workouts are always 10 points
                }
            )
            bonus_created += 1
        
        if bonus_created > 0:
            self.stdout.write(f"  ✓ Created {bonus_created} bonus workouts ({activity_type})")

    def handle(self, *args, **options):
        reset = options["reset"]

        if reset:
            ChallengeBonusWorkout.objects.all().delete()
            ChallengeWorkoutAssignment.objects.all().delete()
            Challenge.objects.all().delete()
            self.stdout.write(self.style.WARNING("Reset: deleted existing challenges, workout assignments, and bonus workouts."))

        # Get default template (first available)
        default_template = PlanTemplate.objects.first()

        for challenge_data in CHALLENGES:
            # Try to get template by name match, otherwise use default
            template_name_map = {
                "Foundation Builder": "3 Rides a Week",
                "Power Base": "4 Rides a Week",
                "Flex Flow": "3 Runs a Week",
                "Dual Zone": "2 Runs 2 Rides",
                "Strength Foundation": "Kegels and Strength",
                "Mindful Movement": "Kegels and Yoga",
                "Complete Base": "Complete Pelvic Health Challenge",  # This might not exist, will use default
                "Balanced Base": "2 Runs 2 Rides",
            }
            
            template = None
            for key, template_name in template_name_map.items():
                if key in challenge_data["name"]:
                    try:
                        template = PlanTemplate.objects.get(name=template_name)
                        break
                    except PlanTemplate.DoesNotExist:
                        pass
            
            if not template:
                template = default_template

            challenge, created = Challenge.objects.update_or_create(
                name=challenge_data["name"],
                defaults={
                    "description": challenge_data["description"],
                    "challenge_type": challenge_data["challenge_type"],
                    "categories": challenge_data["categories"],
                    "start_date": challenge_data["start_date"],
                    "end_date": challenge_data["end_date"],
                    "is_active": challenge_data["is_active"],
                    "default_template": template,
                }
            )
            
            # Set available templates - add all templates as available for seeded challenges
            if created or not challenge.available_templates.exists():
                all_templates = PlanTemplate.objects.all()
                challenge.available_templates.set(all_templates)
            
            # Create Peloton workout assignments for testing
            # Only create if challenge was just created, or if reset flag is used
            if created or reset:
                # Delete existing assignments first if resetting
                if reset:
                    ChallengeWorkoutAssignment.objects.filter(challenge=challenge).delete()
                    ChallengeBonusWorkout.objects.filter(challenge=challenge).delete()
                self._create_workout_assignments(challenge)
                self._create_bonus_workouts(challenge)
            
            # Generate placeholder image
            if challenge_data.get("image_url"):
                try:
                    # Color mapping based on challenge name
                    color_map = {
                        "Foundation Builder": ("4ECDC4", "FFFFFF"),
                        "Power Base": ("FF6B6B", "FFFFFF"),
                        "Flex Flow": ("9370DB", "FFFFFF"),
                        "Dual Zone": ("FF8C00", "000000"),
                        "Strength Foundation": ("8B0000", "FFFFFF"),
                        "Mindful Movement": ("4ECDC4", "FFFFFF"),
                        "Complete Base": ("FF4500", "FFFFFF"),
                        "Balanced Base": ("FFD700", "000000"),
                    }
                    
                    # Find matching color
                    bg_color, text_color = "4A5568", "FFFFFF"
                    for key, colors in color_map.items():
                        if key in challenge.name:
                            bg_color, text_color = colors
                            break
                    
                    # Try to extract from URL if available (format: /400x300/BGCOLOR/TEXTCOLOR?text=TEXT)
                    url = challenge_data["image_url"]
                    if "/" in url:
                        parts = url.split("/")
                        # Find parts that look like hex colors (6 hex digits)
                        import re
                        hex_pattern = re.compile(r'^[0-9A-Fa-f]{6}$')
                        for part in parts:
                            clean_part = part.split("?")[0]
                            if hex_pattern.match(clean_part):
                                if bg_color == "4A5568":  # Only use if we haven't found a match
                                    bg_color = clean_part.upper()
                                elif text_color == "FFFFFF":
                                    text_color = clean_part.upper()
                    
                    # Create badge-like image (square, rounded corners effect)
                    # Badge size: 300x300 for a square badge
                    badge_size = 300
                    img = Image.new('RGB', (badge_size, badge_size), color=f"#{bg_color}")
                    draw = ImageDraw.Draw(img)
                    
                    # Create rounded rectangle effect (simulate with multiple rectangles)
                    border_width = 8
                    # Outer border
                    draw.rectangle([0, 0, badge_size-1, badge_size-1], outline=f"#{text_color}", width=border_width)
                    # Inner highlight for badge effect
                    highlight_color = self._lighten_color(bg_color)
                    draw.rectangle([border_width, border_width, badge_size-border_width-1, badge_size-border_width-1], 
                                 outline=highlight_color, width=2)
                    
                    # Try to use a bold font
                    font_size = 36
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                    except:
                        try:
                            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                        except:
                            font = ImageFont.load_default()
                    
                    # Get text from challenge name - shorter for badge
                    text = challenge.name.replace("'", "").replace(":", "").replace("N'", "N").upper()
                    # Remove "THE ONE WITH" prefix for shorter badge text
                    if "THE ONE WITH" in text:
                        text = text.replace("THE ONE WITH", "").strip()
                    # Split into lines if too long
                    words = text.split()
                    lines = []
                    current_line = ""
                    for word in words:
                        test_line = f"{current_line} {word}".strip() if current_line else word
                        bbox = draw.textbbox((0, 0), test_line, font=font)
                        if bbox[2] - bbox[0] < badge_size - 40:  # Leave padding
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)
                    
                    # Limit to 3 lines max for badge
                    if len(lines) > 3:
                        lines = lines[:3]
                    
                    # Draw text lines (centered)
                    total_height = len(lines) * (font_size + 8)
                    start_y = (badge_size - total_height) // 2
                    
                    for i, line in enumerate(lines):
                        bbox = draw.textbbox((0, 0), line, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        x = (badge_size - text_width) // 2
                        y = start_y + i * (font_size + 8)
                        # Add text shadow for depth
                        draw.text((x+2, y+2), line, fill="#000000" if text_color != "000000" else "#FFFFFF", font=font)
                        draw.text((x, y), line, fill=f"#{text_color}", font=font)
                    
                    # Save to BytesIO
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    # Save to challenge
                    image_name = f"{challenge.name.lower().replace(' ', '_').replace("'", '').replace(':', '').replace('+', '_').replace(' ', '_')}.png"
                    challenge.image.save(
                        image_name,
                        ContentFile(img_buffer.read()),
                        save=True
                    )
                    self.stdout.write(f"  ✓ Generated placeholder image for {challenge.name}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Error generating image for {challenge.name}: {e}"))
            
            status = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{status} Challenge: {challenge.name} "
                    f"({challenge.start_date} - {challenge.end_date}, "
                    f"{'ACTIVE' if challenge.is_currently_running else 'PAST'})"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"\nDone. Seeded {len(CHALLENGES)} challenges."))
