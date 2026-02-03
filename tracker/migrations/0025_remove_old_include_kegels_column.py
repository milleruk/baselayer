# Generated manually on 2026-02-02

from django.db import migrations


def remove_old_column(apps, schema_editor):
    """Remove the old include_kegels column by recreating the table"""
    db_alias = schema_editor.connection.alias
    
    # Disable foreign key checks for this operation
    schema_editor.execute("PRAGMA foreign_keys=OFF;")
    
    # SQLite doesn't support DROP COLUMN, so we need to recreate the table
    schema_editor.execute("""
        CREATE TABLE tracker_challengeinstance_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            selected_template_id INTEGER,
            include_recovery_sessions BOOLEAN NOT NULL DEFAULT 1,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            is_active BOOLEAN NOT NULL DEFAULT 1
        );
    """)
    
    # Copy data from old table to new table
    schema_editor.execute("""
        INSERT INTO tracker_challengeinstance_new 
            (id, user_id, challenge_id, selected_template_id, include_recovery_sessions, started_at, completed_at, is_active)
        SELECT 
            id, user_id, challenge_id, selected_template_id, include_recovery_sessions, started_at, completed_at, is_active
        FROM tracker_challengeinstance;
    """)
    
    # Drop old table
    schema_editor.execute("DROP TABLE tracker_challengeinstance;")
    
    # Rename new table
    schema_editor.execute("ALTER TABLE tracker_challengeinstance_new RENAME TO tracker_challengeinstance;")
    
    # Recreate indexes
    schema_editor.execute("""
        CREATE INDEX tracker_challengeinstance_user_id_idx ON tracker_challengeinstance(user_id);
    """)
    schema_editor.execute("""
        CREATE INDEX tracker_challengeinstance_challenge_id_idx ON tracker_challengeinstance(challenge_id);
    """)
    
    # Re-enable foreign key checks
    schema_editor.execute("PRAGMA foreign_keys=ON;")


def reverse_migration(apps, schema_editor):
    """Reverse is not supported - would require recreating include_kegels column"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0024_delete_kegel_exercises_and_items"),
    ]

    operations = [
        migrations.RunPython(remove_old_column, reverse_migration),
    ]
