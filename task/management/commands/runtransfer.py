from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand

from task.baidupcs import get_baidupcs_client
from task.models import Task
from task.leecher import transfer


class Command(BaseCommand):
    help = "run transfer, save shared_link to Baidu Pan"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="run transfer for exists tasks and exit immediately.",
        )

    def handle(self, *args, **options):
        client = get_baidupcs_client()
        while True:
            tasks = Task.objects.filter(status=Task.Status.INITED)
            for task in tasks:
                transfer(client, task)

            if options["once"]:
                return
            sleep(settings.DOWNLOADER_SLEEP_SECONDS)
