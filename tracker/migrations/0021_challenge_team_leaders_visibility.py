# Generated manually
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0020_remove_challenge_available_templates_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE tracker_challenge ADD COLUMN team_leaders_can_see_users BOOLEAN DEFAULT FALSE NOT NULL;",
                "ALTER TABLE tracker_challenge ADD COLUMN team_leaders_see_users_date DATE NULL;",
            ],
            reverse_sql=[
                "ALTER TABLE tracker_challenge DROP COLUMN IF EXISTS team_leaders_can_see_users;",
                "ALTER TABLE tracker_challenge DROP COLUMN IF EXISTS team_leaders_see_users_date;",
            ],
        ),
    ]
