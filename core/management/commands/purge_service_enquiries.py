from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import ServiceEnquiry


class Command(BaseCommand):
    help = "Review or delete service enquiries older than the configured retention period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=settings.SERVICE_ENQUIRY_RETENTION_DAYS,
            help="Retention period in days (default: SERVICE_ENQUIRY_RETENTION_DAYS).",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Delete matching enquiries. Without this flag, only report the records that would be deleted.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days < 1:
            raise CommandError("--days must be a positive number.")

        cutoff = timezone.now() - timedelta(days=days)
        old_enquiries = ServiceEnquiry.objects.filter(created_at__lt=cutoff)
        count = old_enquiries.count()
        if options["execute"]:
            deleted, _ = old_enquiries.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} database record(s) older than {days} days."))
        else:
            self.stdout.write(f"Dry run: {count} service enquiry record(s) are older than {days} days and would be deleted.")
            self.stdout.write("Run again with --execute to delete them.")
