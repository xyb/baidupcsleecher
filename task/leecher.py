import logging

from django.conf import settings
from django.utils import timezone

from .baidupcs import BaiduPCSClient
from .baidupcs import CaptchaRequired
from .callback import callback
from .models import Task
from .utils import handle_exception

logger = logging.getLogger(__name__)


def start_task(task: Task) -> None:
    task.status = Task.Status.STARTED
    task.started_at = timezone.now()
    task.save()


def save_link(client: "BaiduPCSClient", task: Task) -> None:
    def save_captcha(captcha_id, captcha_img_url, content):
        task.captcha_required = True
        task.captcha = content
        task.captcha_id = captcha_id
        task.captcha_url = captcha_img_url
        task.save()
        callback(task, "captcha_required")

    if (settings.TRANSFER_POLICY == "if_not_present") and client.list_files(
        task.remote_path,
        retry=0,
        fail_silent=True,
    ):
        logger.info(f"save {task} skipped, already exists.")
    else:
        client.save_shared_link(
            task.remote_path,
            task.shared_link,
            task.shared_password,
            callback_save_captcha=save_captcha,
            captcha_id=task.captcha_id or "",
            captcha_code=task.captcha_code or "",
        )
    task.transfer_completed_at = timezone.now()
    task.save()
    logger.info(f"save {task} succeeded.")
    callback(task, "link_saved")


def set_files(client: "BaiduPCSClient", task: Task) -> None:
    task.set_files(list(client.list_files(task.remote_path)))
    task.file_listed_at = timezone.now()
    task.save()
    logger.info(f"list {task} files succeeded.")
    callback(task, "files_ready")


def download_samples(client: "BaiduPCSClient", task: Task) -> None:
    logger.info("downloading samples...")
    client.leech(
        remote_dir=task.remote_path,
        local_dir=settings.DATA_DIR / task.sample_path,
        sample_size=settings.SAMPLE_SIZE,
    )
    task.sample_downloaded_at = timezone.now()
    task.save()
    logger.info(f"sample of {task} downloaded.")
    callback(task, "sampling_downloaded")


def download(client: "BaiduPCSClient", task: Task) -> None:
    logger.info("downloading...")
    client.leech(
        remote_dir=task.remote_path,
        local_dir=task.data_path,
        sample_size=0,
    )
    task.full_downloaded_at = timezone.now()
    task.save()
    logger.info(f"leech {task} succeeded.")


def task_failed(task: Task, message: str) -> None:
    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.failed = True
    task.message = message[: Task._meta.get_field("message").max_length]
    task.save()


def finish_transfer(task: Task) -> None:
    task.status = Task.Status.TRANSFERRED
    task.save()


def transfer(client: "BaiduPCSClient", task: Task) -> None:
    logger.info(f"start transfer {task} ...")
    start_task(task)

    try:
        save_link(client, task)
        set_files(client, task)
        finish_transfer(task)
        logger.info(f"transfer {task} succeed.")
    except CaptchaRequired:
        logging.info(f"captcha required: {task}")
    except Exception as e:
        logging.error(f"transfer {task} failed.")
        task_failed(task, handle_exception(e))


def finish_sampling(task: Task) -> None:
    task.status = Task.Status.SAMPLING_DOWNLOADED
    task.save()


def sampling(client: "BaiduPCSClient", task: Task) -> None:
    logger.info(f"start download sampling of {task}")

    try:
        download_samples(client, task)
    except Exception as e:
        logging.error(f"download sampling of {task} failed.")
        task_failed(task, handle_exception(e))

    finish_sampling(task)
    logger.info(f"download sampling of {task} succeed.")


def finish_task(task: Task) -> None:
    task.status = Task.Status.FINISHED
    task.finished_at = timezone.now()
    task.save()


def leech(client: "BaiduPCSClient", task: Task) -> None:
    logger.info(f"start leech {task} to {task.data_path}")

    try:
        download(client, task)
    except Exception as e:
        logging.error(f"download all files of {task} failed.")
        task_failed(task, handle_exception(e))
        return

    finish_task(task)
    callback(task, "files_downloaded")
    logger.info(f"leech {task} to {task.data_path} succeed.")
