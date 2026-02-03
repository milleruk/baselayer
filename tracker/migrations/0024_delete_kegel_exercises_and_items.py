# Generated manually on 2026-02-02

from django.db import migrations


def delete_kegel_data(apps, schema_editor):
    """Delete all Kegel-related exercises and DailyPlanItems"""
    # Get models
    Exercise = apps.get_model("plans", "Exercise")
    DailyPlanItem = apps.get_model("tracker", "DailyPlanItem")
    
    # Get all Kegel exercises (this needs to be done before we delete them)
    kegel_exercises = Exercise.objects.filter(category="kegel")
    kegel_exercise_ids = list(kegel_exercises.values_list("id", flat=True))
    
    # Delete DailyPlanItems that reference Kegel exercises
    deleted_items = DailyPlanItem.objects.filter(exercise_id__in=kegel_exercise_ids).delete()
    print(f"Deleted {deleted_items[0]} DailyPlanItem records referencing Kegel exercises")
    
    # Delete Kegel exercises
    deleted_exercises = kegel_exercises.delete()
    print(f"Deleted {deleted_exercises[0]} Kegel exercises")


def reverse_delete(apps, schema_editor):
    """This migration cannot be reversed - Kegel data is permanently deleted"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0023_add_recovery_session_fields_to_bonus_workout"),
        ("plans", "0007_update_exercise_categories"),
    ]

    operations = [
        migrations.RunPython(delete_kegel_data, reverse_delete),
    ]
