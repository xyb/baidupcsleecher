import logging
import traceback
from time import sleep

from django.conf import settings
from django.utils import timezone

from task.models import Task

logger = logging.getLogger(__name__)


def start_leech(task):
    logger.info(f"start leech {task.shared_link} to {task.data_path}")
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
            sleep(settings.RUNNER_SLEEP_SECONDS)

    client.save_shared_link(
        task.remote_path,
        task.shared_link,
        task.shared_password,
        callback_save_captcha=save_captcha,
        callback_get_captcha_code=get_captcha_code,
    )
    task.transfer_completed_at = timezone.now()
    task.save()
    logger.info(f"save {task.shared_link} succeeded.")


def set_files(client, task):
    task.set_files(list(client.list_files(task.remote_path)))
    task.file_listed_at = timezone.now()
    task.save()
    logger.info(f"list {task.shared_link} files succeeded.")


def download_samples(client, task):
    logger.info("downloading samples...")
    client.leech(
        remote_dir=task.remote_path,
        local_dir=settings.DATA_DIR / task.sample_path,
        sample_size=10240,
    )
    task.sample_downloaded_at = timezone.now()
    task.save()
    logger.info(f"sample of {task.shared_link} downloaded.")


def download(client, task):
    logger.info("downloading...")
    client.leech(
        remote_dir=task.remote_path,
        local_dir=task.data_path,
        sample_size=0,
    )
    task.full_downloaded_at = timezone.now()
    task.save()
    logger.info(f"leech {task.shared_link} succeeded.")


def handle_exception(task, e):
    message = f"{e}"
    logger.error(message)
    tb = traceback.format_exc()
    logger.error(tb)
    return message


def task_failed(task, message):
    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.failed = True
    task.message = message
    task.save()


def finish_transfer(task):
    task.status = Task.Status.TRANSFERED
    task.save()


def transfer(client, task):
    start_leech(task)

    try:
        save_link(client, task)
        set_files(client, task)
    except Exception as e:
        logging.error(f"transfer {task.shared_link} failed.")
        task_failed(task, handle_exception(task, e))

    finish_transfer(task)


def finish_sampling(task):
    task.status = Task.Status.SAMPLING_DOWNLOADED
    task.save()


def sampling(client, task):
    start_leech(task)

    try:
        download_samples(client, task)
    except Exception as e:
        logging.error(f"download sampling of {task.shared_link} failed.")
        task_failed(task, handle_exception(task, e))

    finish_sampling(task)


def finish_task(task):
    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.save()


def leech(client, task):
    start_leech(task)

    try:
        download(client, task)
    except Exception as e:
        logging.error(f"download all files of {task.shared_link} failed.")
        task_failed(task, handle_exception(task, e))

    finish_task(task)
