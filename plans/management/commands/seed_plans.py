from django.core.management.base import BaseCommand
from plans.models import Exercise, PlanTemplate, PlanTemplateDay
from tracker.models import DailyPlanItem, WeeklyPlan

EXERCISES = [
    # Yoga Recovery Sessions
    {
        "name": "Gentle Flow Yoga",
        "category": "yoga",
        "position": "Mat-based",
        "key_cue": "Movement supports breath rhythm. Core responds naturally to transitions.",
        "reps_hold": "20-30 min",
        "primary_use": "Recovery / mobility",
        "video_url": "",
    },
    {
        "name": "Restorative Yoga",
        "category": "yoga",
        "position": "Supported poses",
        "key_cue": "Passive holds release tension. Breathe deeply into tight areas.",
        "reps_hold": "20-30 min",
        "primary_use": "Deep recovery",
        "video_url": "",
    },
    {
        "name": "Hip Mobility Flow",
        "category": "yoga",
        "position": "Mat-based",
        "key_cue": "Hips open gradually. Core stability responds to movement challenges.",
        "reps_hold": "15-20 min",
        "primary_use": "Hip recovery / cycling",
        "video_url": "",
    },
    {
        "name": "Core Flow Yoga",
        "category": "yoga",
        "position": "Mat-based",
        "key_cue": "Core engages with breath. System responds to effort, relaxes between poses.",
        "reps_hold": "20-30 min",
        "primary_use": "Active recovery / core",
        "video_url": "",
    },
    
    # Pilates Core Sessions
    {
        "name": "Foundation Pilates",
        "category": "pilates",
        "position": "Mat-based",
        "key_cue": "Core supports movement from center. Breath coordinates with effort.",
        "reps_hold": "20-30 min",
        "primary_use": "Core integration",
        "video_url": "",
    },
    {
        "name": "Low-Impact Pilates Flow",
        "category": "pilates",
        "position": "Mat-based",
        "key_cue": "Controlled movement patterns. Deep core responds to precision work.",
        "reps_hold": "20-30 min",
        "primary_use": "Recovery / control",
        "video_url": "",
    },
    {
        "name": "Pilates Core Strength",
        "category": "pilates",
        "position": "Mat-based",
        "key_cue": "Systematic core loading. System stabilizes under controlled stress.",
        "reps_hold": "20-30 min",
        "primary_use": "Core development",
        "video_url": "",
    },
    
    # Breathwork Sessions
    {
        "name": "Box Breathing Practice",
        "category": "breathwork",
        "position": "Seated or lying",
        "key_cue": "4-count breath cycle. Core naturally responds to diaphragm movement.",
        "reps_hold": "10-15 min",
        "primary_use": "Recovery / nervous system",
        "video_url": "",
    },
    {
        "name": "Diaphragmatic Breathing",
        "category": "breathwork",
        "position": "Seated or lying",
        "key_cue": "Belly expands on inhale. Pelvic floor releases with breath.",
        "reps_hold": "10-15 min",
        "primary_use": "Recovery / relaxation",
        "video_url": "",
    },
    {
        "name": "Breath-Core Connection",
        "category": "breathwork",
        "position": "Seated",
        "key_cue": "Core engages with exhale. System responds naturally to breathing patterns.",
        "reps_hold": "10-20 min",
        "primary_use": "Core-breath integration",
        "video_url": "",
    },
    {
        "name": "Wim Hof Style Breathing",
        "category": "breathwork",
        "position": "Seated or lying",
        "key_cue": "Controlled breath cycles. Core activates with rhythmic breathing.",
        "reps_hold": "15-20 min",
        "primary_use": "Energy / recovery",
        "video_url": "",
    },
    
    # Mobility & Recovery Flows
    {
        "name": "Lower Body Mobility Flow",
        "category": "mobility",
        "position": "Standing/mat-based",
        "key_cue": "Dynamic stretching through full range. Core supports movement throughout.",
        "reps_hold": "15-20 min",
        "primary_use": "Running/cycling recovery",
        "video_url": "",
    },
    {
        "name": "Foam Rolling & Stretching",
        "category": "mobility",
        "position": "Mat with roller",
        "key_cue": "Release tight tissue. Breathe into restricted areas.",
        "reps_hold": "15-20 min",
        "primary_use": "Tissue recovery",
        "video_url": "",
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
        "key_cue": "Slowly rotate pelvis through 'clock' directions.",
        "reps_hold": "1–2 mins",
        "primary_use": "Awareness / release",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
    {
        "name": "Happy Baby Release",
        "category": "yoga",
        "position": "Supine yoga pose",
        "key_cue": "Relax fully; breathe into hips/pelvis.",
        "reps_hold": "60–90s",
        "primary_use": "Recovery / relaxation",
        "video_url": "https://www.youtube.com/watch?v=JFJtUtKQCuM",
    },
]

TEMPLATES = [
    {
        "name": "3 Rides a Week",
        "description": "Three cycling sessions per week with optional recovery sessions",
        "days": [
            (0, "Rest", "Optional: 20 min yoga or breathwork"),  # Sunday
            (1, "PZE (Z2)", ""),  # Monday
            (2, "Rest", "Optional: mobility or stretching"),  # Tuesday
            (3, "Power Zone (Z3–Z4)", ""),  # Wednesday
            (4, "Rest", "Optional: gentle yoga flow"),  # Thursday
            (5, "PZE (Z2)", ""),  # Friday
            (6, "Rest", "Recovery: restorative yoga or breathwork"),  # Saturday
        ],
    },
    {
        "name": "4 Rides a Week",
        "description": "Four cycling sessions per week with optional recovery sessions",
        "days": [
            (0, "PZE (Z2)", ""),  # Sunday
            (1, "PZE (Z2)", ""),  # Monday
            (2, "Rest", "Optional: 20 min breathwork or mobility"),  # Tuesday
            (3, "Power Zone (Z3–Z4)", ""),  # Wednesday
            (4, "Rest", "Optional: gentle yoga or Pilates"),  # Thursday
            (5, "Power Zone (Z3–Z4)", ""),  # Friday
            (6, "Rest", "Recovery: foam rolling & stretching"),  # Saturday
        ],
    },
    {
        "name": "3 Runs a Week",
        "description": "Three running sessions per week with optional recovery sessions",
        "days": [
            (0, "Rest", "Optional: 20 min yoga or breathwork"),  # Sunday
            (1, "Run Tempo", ""),  # Monday
            (2, "Rest", "Optional: hip mobility flow"),  # Tuesday
            (3, "Run Endurance", ""),  # Wednesday
            (4, "Rest", "Optional: foam rolling & stretching"),  # Thursday
            (5, "Run Intervals", ""),  # Friday
            (6, "Rest", "Recovery: restorative yoga"),  # Saturday
        ],
    },
    {
        "name": "Recovery & Mobility",
        "description": "Focus on recovery, yoga, Pilates, and breathwork",
        "days": [
            (0, "Rest", "Optional: breathwork"),  # Sunday
            (1, "Yoga Flow", "Gentle flow or hip mobility"),  # Monday
            (2, "Breathwork", "Box breathing or diaphragmatic"),  # Tuesday
            (3, "Pilates", "Foundation or low-impact flow"),  # Wednesday
            (4, "Mobility", "Lower body mobility flow"),  # Thursday
            (5, "Yoga", "Core flow or restorative"),  # Friday
            (6, "Recovery", "Foam rolling & stretching"),  # Saturday
        ],
    },
    {
        "name": "Yoga & Core",
        "description": "Yoga and Pilates sessions with optional breathwork",
        "days": [
            (0, "Rest", "Optional: breathwork or meditation"),  # Sunday
            (1, "Yoga Flow", "Active flow with core focus"),  # Monday
            (2, "Pilates", "Foundation Pilates"),  # Tuesday
            (3, "Yoga", "Hip mobility flow"),  # Wednesday
            (4, "Pilates", "Core strength focus"),  # Thursday
            (5, "Yoga", "Gentle flow or restorative"),  # Friday
            (6, "Rest", "Recovery: breathwork or stretching"),  # Saturday
        ],
    },
    {
        "name": "Strength & Recovery",
        "description": "Strength training combined with recovery sessions",
        "days": [
            (0, "Rest", "Optional: gentle yoga"),  # Sunday
            (1, "Strength Upper", ""),  # Monday
            (2, "Recovery", "Yoga or breathwork"),  # Tuesday
            (3, "Strength Lower", ""),  # Wednesday
            (4, "Recovery", "Pilates or mobility"),  # Thursday
            (5, "Strength Full Body", ""),  # Friday
            (6, "Rest", "Recovery: foam rolling & stretching"),  # Saturday
        ],
    },
    {
        "name": "2 Runs 2 Rides",
        "description": "Two running and two cycling sessions per week with optional recovery",
        "days": [
            (0, "PZE (Z2)", ""),  # Sunday - Ride
            (1, "Run Tempo", ""),  # Monday - Run
            (2, "Rest", "Optional: yoga or breathwork"),  # Tuesday
            (3, "Run Endurance", ""),  # Wednesday - Run
            (4, "Rest", "Optional: mobility or Pilates"),  # Thursday
            (5, "Power Zone (Z3–Z4)", ""),  # Friday - Ride
            (6, "Rest", "Recovery: restorative yoga or stretching"),  # Saturday
        ],
    },
]

class Command(BaseCommand):
    help = "Seeds exercises and plan templates with recovery-focused content."

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
