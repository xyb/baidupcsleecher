import sys
import traceback
from time import sleep

from django.conf import settings
from django.utils import timezone

from task.models import Task


def start_leech(task):
    print(f"start leech {task.shared_link} to {task.data_path}")
    task.status = Task.Status.STARTED
    task.started_at = timezone.now()
    task.save()


def save_link(client, task):
    def save_captcha(content):
        task.captcha_required = True
        task.captcha = content
        open('/tmp/captcha.png', 'wb').write(content)
        task.save()

    def get_captcha_code():
        while True:
            new = Task.objects.get(id=task.id)
            if new.captcha_code:
                new.captcha_required = False
                new.save()
                return new.captcha_code
            sleep(settings.DOWNLOADER_SLEEP_SECONDS)

    client.save_shared_link(
        task.remote_path,
        task.shared_link,
        task.shared_password,
        callback_save_captcha=save_captcha,
        callback_get_captcha_code=get_captcha_code,
    )
    task.transfer_completed_at = timezone.now()
    task.save()
    print(f"save {task.shared_link} succeeded.")


def set_files(client, task):
    task.set_files(list(client.list_files(task.remote_path)))
    task.file_listed_at = timezone.now()
    task.save()
    print(f"list {task.shared_link} files succeeded.")


def download_samples(client, task):
    print("downloading samples...")
    client.leech(
        remote_dir=task.remote_path,
        local_dir=settings.DATA_DIR / task.sample_path,
        sample_size=10240,
    )
    task.sample_downloaded_at = timezone.now()
    task.save()
    print(f"sample of {task.shared_link} downloaded.")


def download_all(client, task):
    print("downloading...")
    client.leech(
        remote_dir=task.remote_path,
        local_dir=task.data_path,
        sample_size=0,
    )
    task.full_downloaded_at = timezone.now()
    task.save()
    print(f"leech {task.shared_link} succeeded.")


def handle_exception(task, e):
    print(f"leech {task.shared_link} failed.")
    tb = traceback.format_exc()
    message = f"{e}"
    print(message, file=sys.stderr)
    print(tb, file=sys.stderr)
    return message


def task_failed(task, message):
    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.failed = True
    task.message = message
    task.save()


def finish_transfer(task):
    task.status = Task.Status.TRANSFERED
    task.finished_at = timezone.now()
    task.save()


def transfer(client, task):
    start_leech(task)

    try:
        save_link(client, task)
        set_files(client, task)
        download_samples(client, task)
    except Exception as e:
        task_failed(task, handle_exception(e))

    finish_transfer(task)


def finish_sampling(task):
    task.status = Task.Status.SAMPLING_DOWNLOADED
    task.finished_at = timezone.now()
    task.save()


def sampling(client, task):
    start_leech(task)

    try:
        save_link(client, task)
        set_files(client, task)
        download_samples(client, task)
    except Exception as e:
        task_failed(task, handle_exception(e))

    finish_transfer(task)


def finish_task(task):
    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.save()


def leech(client, task):
    start_leech(task)

    try:
        download_samples(client, task)
        download_all(client, task)
    except Exception as e:
        task_failed(task, handle_exception(e))

    finish_task(task)
