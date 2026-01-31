from django.core.management.base import BaseCommand

from recommender.services import INSTRUCTORS_SOURCE_URL, write_local_instructors_json


class Command(BaseCommand):
    help = "Fetch Pelovibe instructor list and write local JSON dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-url",
            default=INSTRUCTORS_SOURCE_URL,
            help="URL to instructors.ts (default: upstream repo raw URL).",
        )

    def handle(self, *args, **options):
        source_url = options["source_url"]
        count = write_local_instructors_json(source_url=source_url)
        self.stdout.write(self.style.SUCCESS(f"Wrote {count} instructors to local JSON dataset."))

