from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand

from task.baidupcs import get_baidupcs_client
from task.leecher import transfer
from task.models import Task


class Command(BaseCommand):
    help = "save shared link to Baidu Pan"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="run transfer for exists tasks and exit immediately.",
        )

    def handle(self, *args, **options):
        client = get_baidupcs_client()
        while True:
            for task in Task.filter_inited():
                transfer(client, task)

            if options["once"]:
                return
            sleep(settings.RUNNER_SLEEP_SECONDS)
