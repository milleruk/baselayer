import csv
import os
import sys
from datetime import datetime
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from workouts.models import Workout

User = get_user_model()

def main(csv_path, username):
    try:
        user = User.objects.get(email=username)
    except User.DoesNotExist:
        print(f'User "{username}" does not exist')
        return

    # Read CSV workout dates
    csv_dates = set()
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = row.get('Workout Timestamp') or row.get('Timestamp') or row.get('Date')
            if not date_str:
                continue
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except Exception:
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                except Exception:
                    continue
            csv_dates.add(dt.date())

    # Get DB workout dates
    db_dates = set(
        Workout.objects.filter(user=user, completed_at__isnull=False)
        .values_list('completed_at', flat=True)
    )
    db_dates = set(dt.date() for dt in db_dates if dt)

    # Compare
    missing_in_db = csv_dates - db_dates
    extra_in_db = db_dates - csv_dates

    print(f"Total CSV workout days: {len(csv_dates)}")
    print(f"Total DB workout days: {len(db_dates)}")
    print(f"Days in CSV but missing in DB: {len(missing_in_db)}")
    for d in sorted(missing_in_db):
        print(f"  Missing: {d}")
    print(f"Days in DB but not in CSV: {len(extra_in_db)}")
    for d in sorted(extra_in_db):
        print(f"  Extra: {d}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Cross-check Peloton CSV export with DB workouts by date.')
    parser.add_argument('--csv', type=str, required=True, help='Path to Peloton CSV export')
    parser.add_argument('--username', type=str, required=True, help='Username/email to check')
    args = parser.parse_args()
    main(args.csv, args.username)
