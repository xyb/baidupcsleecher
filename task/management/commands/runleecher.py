from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand

from task.baidupcs import get_baidupcs_client
from task.leecher import leech
from task.models import Task


class Command(BaseCommand):
    help = "run leecher"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="run leecher for exists tasks and exit immediately.",
        )

    def handle(self, *args, **options):
        client = get_baidupcs_client()
        while True:
            tasks = Task.objects.filter(status=Task.Status.INITED)
            for task in tasks:
                leech(client, task)

            if options["once"]:
                return
            sleep(settings.DOWNLOADER_SLEEP_SECONDS)
