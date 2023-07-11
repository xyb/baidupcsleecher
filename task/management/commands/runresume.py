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
            help="resume all failed tasks once and exit immediately.",
        )

    def resume_once(self):
        for task in Task.filter_failed():
            if not task.recoverable:
                continue
            if task.retry_times >= settings.RETRY_TIMES_LIMIT:
                continue
            task.schedule_resume()

    def handle(self, *args, **options):
        logger.info("auto resume failed but recoverable tasks.")
        while True:
            self.resume_once()
            if options["once"]:
                logger.info("auto resume tasks once and exit now.")
                return
            sleep(settings.RUNNER_SLEEP_SECONDS)
