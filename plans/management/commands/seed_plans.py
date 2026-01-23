from django.core.management.base import BaseCommand
from plans.models import Exercise, PlanTemplate, PlanTemplateDay
from tracker.models import DailyPlanItem, WeeklyPlan

EXERCISES = [
    {
        "name": "Basic Kegel",
        "category": "kegel",
        "position": "Lying / Seated",
        "key_cue": "Lift pelvic floor up and in (no abs/glutes). Breathe normally.",
        "reps_hold": "5–10 × 3–5s",
        "primary_use": "Foundation",
        "video_url": "https://www.youtube.com/watch?v=MJ7EfGu03-0",
    },
    {
        "name": "Long-Hold Kegel",
        "category": "kegel",
        "position": "Seated / Standing",
        "key_cue": "Lift and hold with steady breathing. Relax fully after.",
        "reps_hold": "5 × 8–20s",
        "primary_use": "Endurance / Sex",
        "video_url": "https://www.youtube.com/watch?v=NTaTPmyLxUY",
    },
    {
        "name": "Pulse Kegels",
        "category": "kegel",
        "position": "Standing",
        "key_cue": "Quick 1s lift → full relax. Keep glutes/thighs quiet.",
        "reps_hold": "10–20 reps",
        "primary_use": "Running reflex / control",
        "video_url": "https://www.youtube.com/watch?v=c0aDJrSiR1A",
    },
    {
        "name": "Elevator Kegels",
        "category": "kegel",
        "position": "Seated",
        "key_cue": "Lift in 3–4 stages (‘floors’), pause, then slow release.",
        "reps_hold": "5–8 reps",
        "primary_use": "Control / coordination",
        "video_url": "https://www.youtube.com/watch?v=n6z88aU1dMw",
    },
    {
        "name": "Reverse Kegels",
        "category": "kegel",
        "position": "Any (best lying)",
        "key_cue": "Relax and 'open' pelvic floor. Gentle—no straining.",
        "reps_hold": "10–15 reps",
        "primary_use": "Cycling recovery / reduce tightness",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "The Knack",
        "category": "kegel",
        "position": "Any",
        "key_cue": "Strong contraction immediately before sneezing, coughing, or lifting. Timing is key.",
        "reps_hold": "As needed",
        "primary_use": "Stress incontinence prevention",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Wave Kegels",
        "category": "kegel",
        "position": "Seated / Lying",
        "key_cue": "Contract front to back (or back to front) in a wave motion. Focus on coordination.",
        "reps_hold": "8–10 reps each direction",
        "primary_use": "Coordination / awareness",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Side-to-Side Kegels",
        "category": "kegel",
        "position": "Seated",
        "key_cue": "Contract left side, then right side. Keep center relaxed. Alternate smoothly.",
        "reps_hold": "10 reps each side",
        "primary_use": "Lateral coordination / balance",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Progressive Kegels",
        "category": "kegel",
        "position": "Lying / Seated",
        "key_cue": "Start at 30% strength, build to 50%, then 70%, then 100%. Hold each level 3s, then release slowly.",
        "reps_hold": "5–8 reps",
        "primary_use": "Strength building / control",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Quick Flicks",
        "category": "kegel",
        "position": "Standing",
        "key_cue": "Very rapid contractions (0.5s) with full release. Train fast-twitch fibers.",
        "reps_hold": "20–30 reps",
        "primary_use": "Fast-twitch / reaction speed",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Pelvic Tilts",
        "category": "mobility",
        "position": "Supine",
        "key_cue": "Tilt pelvis to flatten low back; move slowly and relax.",
        "reps_hold": "10 reps",
        "primary_use": "Mobility / release",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Pelvic Clocks",
        "category": "mobility",
        "position": "Supine",
        "key_cue": "Slowly rotate pelvis through ‘clock’ directions.",
        "reps_hold": "1–2 mins",
        "primary_use": "Awareness / release",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Happy Baby Release",
        "category": "yoga",
        "position": "Supine yoga pose",
        "key_cue": "Relax pelvic floor fully; breathe into hips/pelvis.",
        "reps_hold": "60–90s",
        "primary_use": "Recovery / relaxation",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
]

TEMPLATES = [
    {
        "name": "3 Rides a Week",
        "description": "Three cycling sessions per week with pelvic floor exercises",
        "days": [
            (0, "Rest", "Optional: reverse + pelvic clocks"),  # Sunday
            (1, "PZE (Z2)", "Post-ride: reverse kegels + tilts"),  # Monday
            (2, "Rest", "Optional: basic kegels"),  # Tuesday
            (3, "Power Zone (Z3–Z4)", "Post-ride: long-holds + reverse"),  # Wednesday
            (4, "Rest", "Optional: mobility work"),  # Thursday
            (5, "PZE (Z2)", "Post-ride: elevator + reverse"),  # Friday
            (6, "Rest", "Recovery: reverse + pelvic clocks"),  # Saturday
        ],
    },
    {
        "name": "4 Rides a Week",
        "description": "Four cycling sessions per week with pelvic floor exercises",
        "days": [
            (0, "PZE (Z2)", "Post-ride: reverse kegels + tilts"),  # Sunday
            (1, "PZE (Z2)", "Post-ride: reverse kegels + tilts"),  # Monday
            (2, "Rest", "Optional: basic kegels"),  # Tuesday
            (3, "Power Zone (Z3–Z4)", "Post-ride: long-holds + reverse"),  # Wednesday
            (4, "Rest", "Optional: mobility work"),  # Thursday
            (5, "Power Zone (Z3–Z4)", "Post-ride: pulses + long-holds"),  # Friday
            (6, "Rest", "Recovery: reverse + pelvic clocks"),  # Saturday
        ],
    },
    {
        "name": "3 Runs a Week",
        "description": "Three running sessions per week with pelvic floor exercises",
        "days": [
            (0, "Rest", "Optional: reverse + pelvic clocks"),  # Sunday
            (1, "Run Tempo", "Post-run: pulses + short long-holds"),  # Monday
            (2, "Rest", "Optional: basic kegels"),  # Tuesday
            (3, "Run Endurance", "Post-run: pulses + elevator"),  # Wednesday
            (4, "Rest", "Optional: mobility work"),  # Thursday
            (5, "Run Intervals", "Post-run: quick flicks + long-holds"),  # Friday
            (6, "Rest", "Recovery: reverse + pelvic clocks"),  # Saturday
        ],
    },
    {
        "name": "Just Kegels",
        "description": "Focus on pelvic floor exercises only",
        "days": [
            (0, "Rest", "Optional: reverse + pelvic clocks"),  # Sunday
            (1, "Kegel Focus", "Basic + long-hold kegels"),  # Monday
            (2, "Kegel Focus", "Pulse + elevator kegels"),  # Tuesday
            (3, "Kegel Focus", "Progressive + wave kegels"),  # Wednesday
            (4, "Kegel Focus", "Side-to-side + quick flicks"),  # Thursday
            (5, "Kegel Focus", "The Knack + long-hold"),  # Friday
            (6, "Recovery", "Reverse kegels + pelvic clocks"),  # Saturday
        ],
    },
    {
        "name": "Kegels and Yoga",
        "description": "Pelvic floor exercises combined with yoga sessions",
        "days": [
            (0, "Rest", "Optional: reverse + pelvic clocks"),  # Sunday
            (1, "Yoga Flow", "Post-yoga: reverse + basic kegels"),  # Monday
            (2, "Kegel Focus", "Pulse + elevator kegels"),  # Tuesday
            (3, "Yoga Mobility", "Post-yoga: reverse + pelvic clocks"),  # Wednesday
            (4, "Kegel Focus", "Long-hold + progressive kegels"),  # Thursday
            (5, "Yoga Recovery", "Post-yoga: reverse + happy baby"),  # Friday
            (6, "Rest", "Recovery: reverse + pelvic clocks"),  # Saturday
        ],
    },
    {
        "name": "Kegels and Strength",
        "description": "Pelvic floor exercises combined with strength training",
        "days": [
            (0, "Rest", "Optional: reverse + pelvic clocks"),  # Sunday
            (1, "Strength Upper", "Post-workout: reverse + basic kegels"),  # Monday
            (2, "Kegel Focus", "Pulse + elevator kegels"),  # Tuesday
            (3, "Strength Lower", "Post-workout: reverse + long-holds"),  # Wednesday
            (4, "Kegel Focus", "Progressive + wave kegels"),  # Thursday
            (5, "Strength Full Body", "Post-workout: reverse + the knack"),  # Friday
            (6, "Rest", "Recovery: reverse + pelvic clocks"),  # Saturday
        ],
    },
    {
        "name": "2 Runs 2 Rides",
        "description": "Two running and two cycling sessions per week with pelvic floor exercises",
        "days": [
            (0, "PZE (Z2)", "Post-ride: reverse kegels + tilts"),  # Sunday - Ride
            (1, "Run Tempo", "Post-run: pulses + short long-holds"),  # Monday - Run
            (2, "Rest", "Optional: basic kegels"),  # Tuesday
            (3, "Run Endurance", "Post-run: pulses + elevator"),  # Wednesday - Run
            (4, "Rest", "Optional: mobility work"),  # Thursday
            (5, "Power Zone (Z3–Z4)", "Post-ride: long-holds + reverse"),  # Friday - Ride
            (6, "Rest", "Recovery: reverse + pelvic clocks"),  # Saturday
        ],
    },
]

class Command(BaseCommand):
    help = "Seeds exercises and a default plan template."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing seeded objects first.")

    def handle(self, *args, **options):
        reset = options["reset"]

        if reset:
            # Delete in order to respect foreign key constraints
            DailyPlanItem.objects.all().delete()
            WeeklyPlan.objects.all().delete()
            PlanTemplateDay.objects.all().delete()
            PlanTemplate.objects.all().delete()
            Exercise.objects.all().delete()
            self.stdout.write(self.style.WARNING("Reset: deleted existing exercises/templates/plans."))

        # Exercises
        for data in EXERCISES:
            obj, created = Exercise.objects.update_or_create(
                name=data["name"],
                defaults=data,
            )
            msg = "Created" if created else "Updated"
            self.stdout.write(f"{msg} Exercise: {obj.name}")

        # Templates + days
        for template_data in TEMPLATES:
            tpl, created = PlanTemplate.objects.update_or_create(
                name=template_data["name"],
                defaults={"description": template_data["description"]},
            )
            if not created:
                tpl.days.all().delete()

            for dow, focus, notes in template_data["days"]:
                PlanTemplateDay.objects.create(
                    template=tpl,
                    day_of_week=dow,
                    peloton_focus=focus,
                    notes=notes,
                )
            self.stdout.write(self.style.SUCCESS(f"Seeded template: {tpl.name} (7 days)"))
        
        self.stdout.write(self.style.SUCCESS("Done."))
