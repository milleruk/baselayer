# Generated manually on 2026-02-02

from django.db import migrations


def rename_column(apps, schema_editor):
    """Rename include_kegels to include_recovery_sessions using database-agnostic approach"""
    db_alias = schema_editor.connection.alias
    
    # For SQLite, we need to recreate the table (SQLite doesn't support RENAME COLUMN directly in older versions)
    # But Django's schema editor handles this for us if we use raw SQL carefully
    
    # Get database vendor
    vendor = schema_editor.connection.vendor
    
    if vendor == 'sqlite':
        # SQLite: Create new column, copy data, drop old column
        schema_editor.execute(
            "ALTER TABLE tracker_challengeinstance ADD COLUMN include_recovery_sessions BOOLEAN NOT NULL DEFAULT 1;"
        )
        schema_editor.execute(
            "UPDATE tracker_challengeinstance SET include_recovery_sessions = include_kegels;"
        )
        # Note: SQLite doesn't support DROP COLUMN in older versions, but Django handles this
    else:
        # PostgreSQL/MySQL support RENAME COLUMN
        schema_editor.execute(
            "ALTER TABLE tracker_challengeinstance RENAME COLUMN include_kegels TO include_recovery_sessions;"
        )


def reverse_rename(apps, schema_editor):
    """Reverse the rename"""
    vendor = schema_editor.connection.vendor
    
    if vendor == 'sqlite':
        schema_editor.execute(
            "ALTER TABLE tracker_challengeinstance ADD COLUMN include_kegels BOOLEAN NOT NULL DEFAULT 1;"
        )
        schema_editor.execute(
            "UPDATE tracker_challengeinstance SET include_kegels = include_recovery_sessions;"
        )
    else:
        schema_editor.execute(
            "ALTER TABLE tracker_challengeinstance RENAME COLUMN include_recovery_sessions TO include_kegels;"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0021_challenge_team_leaders_visibility"),
    ]

    operations = [
        migrations.RunPython(rename_column, reverse_rename),
    ]
