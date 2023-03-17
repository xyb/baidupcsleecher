from time import sleep
import sys
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

    def callback_save_captcha(content):
        task.captcha_required = True
        task.captcha = content
        open('/tmp/captcha.png', 'wb').write(content)
        task.save()

    def callback_get_captcha_code():
        while True:
            new = Task.objects.get(id=task.id)
            if new.captcha_code:
                new.captcha_required = False
                new.save()
                return new.captcha_code
            sleep(settings.DOWNLOADER_SLEEP_SECONDS)

    failed = False
    message = ""
    try:
        client.save_shared_link(
            task.remote_path,
            task.shared_link,
            task.shared_password,
            callback_save_captcha=callback_save_captcha,
            callback_get_captcha_code=callback_get_captcha_code,
        )
        task.transfer_completed_at = timezone.now()
        task.save()
        print(f"save {task.shared_link} succeeded.")

        task.set_files(list(client.list_files(task.remote_path)))
        task.file_listed_at = timezone.now()
        task.save()
        print(f"list {task.shared_link} files succeeded.")

        print("downloading samples...")
        client.leech(
            remote_dir=task.remote_path,
            local_dir=settings.DATA_DIR / task.sample_path,
            sample_size=10240,
        )
        task.sample_downloaded_at = timezone.now()
        task.save()
        print(f"sample of {task.shared_link} downloaded.")

        print("downloading...")
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
        print(message, file=sys.stderr)
        print(tb, file=sys.stderr)

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
