import logging
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand

from task.baidupcs import get_baidupcs_client
from task.leecher import leech
from task.models import Task

logger = logging.getLogger("runleecher")


class Command(BaseCommand):
    help = "download all files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="run leecher for exists tasks and exit immediately.",
        )

    def handle(self, *args, **options):
        logger.info("leecher started.")
        client = get_baidupcs_client()
        while True:
            for task in Task.filter_sampling_downloaded():
                leech(client, task)

            if options["once"]:
                return
            sleep(settings.RUNNER_SLEEP_SECONDS)
