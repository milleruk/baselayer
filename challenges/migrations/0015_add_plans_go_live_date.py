# Generated manually for adding plans_go_live_date field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('challenges', '0005_alter_team_leader'),  # Latest migration in challenges app
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE tracker_challenge 
                ADD COLUMN plans_go_live_date DATE NULL;
            """,
            reverse_sql="""
                ALTER TABLE tracker_challenge 
                DROP COLUMN plans_go_live_date;
            """
        ),
    ]
