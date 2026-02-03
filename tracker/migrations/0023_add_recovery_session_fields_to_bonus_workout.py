# Generated manually on 2026-02-02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0022_rename_include_kegels_to_recovery_sessions"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE tracker_challengebonusworkout 
            ADD COLUMN duration_minutes INTEGER NULL;
            """,
            reverse_sql="ALTER TABLE tracker_challengebonusworkout DROP COLUMN duration_minutes;",
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE tracker_challengebonusworkout 
            ADD COLUMN is_recovery BOOLEAN NOT NULL DEFAULT false;
            """,
            reverse_sql="ALTER TABLE tracker_challengebonusworkout DROP COLUMN is_recovery;",
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE tracker_challengebonusworkout 
            ADD COLUMN category_restriction VARCHAR(100) NOT NULL DEFAULT '';
            """,
            reverse_sql="ALTER TABLE tracker_challengebonusworkout DROP COLUMN category_restriction;",
        ),
    ]
