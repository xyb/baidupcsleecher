import logging
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand

from task.models import Task

logger = logging.getLogger("runresume")


class Command(BaseCommand):
    help = "resume failed but recoverable tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="run .",
        )

    def handle(self, *args, **options):
        logger.info("auto resume failed but recoverable tasks.")
        while True:
            for task in Task.filter_failed():
                if not task.recoverable:
                    continue
                if task.retry_times >= settings.RETRY_TIMES_LIMIT:
                    continue
                task.resume()

            if options["once"]:
                return
            sleep(settings.RUNNER_SLEEP_SECONDS)
