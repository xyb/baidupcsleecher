from time import sleep
import json
import traceback

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from task.baidupcs import BaiduPCS
from task.models import Task
from task.utils import cookies2dict



def leech(client, task):
    print(f"start leech {task.shared_link} to {task.data_path}")
    task.status = Task.Status.STARTED
    task.started_at = timezone.now()
    task.save()

    failed = False
    message = ""
    try:
        print(task.remote_path)
        client.save_shared_link(
            task.remote_path,
            task.shared_link,
            task.shared_password,
        )
        task.transfer_completed_at = timezone.now()
        task.save()
        print(f"save {task.shared_link} succeeded.")

        task.files = json.dumps(list(client.list_files(task.remote_path)))
        task.file_listed_at = timezone.now()
        task.save()
        print(f"list {task.shared_link} files succeeded.")

        client.leech(
            remote_dir=task.remote_path,
            local_dir=task.data_path,
            sample_size=10240,
        )
        task.sample_downloaded_at = timezone.now()
        task.save()
        print(f"sample of {task.shared_link} downloaded.")

        client.leech(
            remote_dir=task.remote_path,
            local_dir=task.data_path,
            sample_size=0,
        )
        task.full_downloaded_at = timezone.now()
        task.save()
        print(f"leech {task.shared_link} succeeded.")
    except Exception as e:
        print(f"leech {task.shared_link} failed.")
        failed = True
        tb = traceback.format_exc()
        message = f"{e}"
        print(message)
        print(tb)

    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.failed = failed
    task.message = message
    task.save()


class Command(BaseCommand):
    help = "run leecher"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="run leecher for exists tasks and exit immediately.",
        )

    def handle(self, *args, **options):
        client = BaiduPCS(
            settings.PAN_BAIDU_BDUSS,
            cookies2dict(settings.PAN_BAIDU_COOKIES),
        )
        while True:
            tasks = Task.objects.filter(status=Task.Status.INITED)
            for task in tasks:
                leech(client, task)

            if options["once"]:
                return
            sleep(settings.DOWNLOADER_SLEEP_SECONDS)
