from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from task.baidupcs import BaiduPCS
from task.models import Task

# import traceback


def convert(task):
    print(f"start leech {task.shared_link} to {task.data_path}")
    task.status = Task.Status.STARTED
    task.started_at = timezone.now()
    task.save()

    failed = False
    message = ""
    try:
        client = BaiduPCS(settings.PAN_BAIDU_BDUSS, settings.PAN_BAIDU_COOKIES)
        client.leech(
            task.shared_link,
            task.shared_password,
            remote_path=task.remote_path,
            local_path=task.data_path,
        )
        print(f"leech {task.shared_link} succeeded.")
    except Exception as e:
        print(f"leech {task.shared_link} failed.")
        failed = True
        # tb = traceback.format_exc()
        # message = f'{e}\n{tb}'
        message = f"{e}"

    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.failed = failed
    task.message = message
    task.save()


class Command(BaseCommand):
    help = "run leecher process"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="run leecher for exists tasks and exit immediately.",
        )

    def handle(self, *args, **options):
        while True:
            tasks = Task.objects.filter(status=Task.Status.INITED)
            for task in tasks:
                convert(task)

            if options["once"]:
                return
            sleep(settings.DOWNLOADER_SLEEP_SECONDS)
