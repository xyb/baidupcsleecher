from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from task.converter import convert2mp3
from task.models import Task

# import traceback


def convert(task):
    print(f"start convert {task.from_path} to {task.to_path}")
    task.status = Task.Status.STARTED
    task.started_at = timezone.now()
    task.save()

    failed = False
    message = ""
    try:
        convert2mp3(
            task.get_full_from_path(),
            task.get_full_to_path(),
        )
        print(f"convert {task.to_path} succeeded.")
    except Exception as e:
        print(f"convert {task.to_path} failed.")
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
            help="run converter for exists tasks and exit immediately.",
        )

    def handle(self, *args, **options):
        while True:
            tasks = Task.objects.filter(status=Task.Status.INITED)
            for task in tasks:
                convert(task)

            if options["once"]:
                return
            sleep(settings.DOWNLOADER_SLEEP_SECONDS)
