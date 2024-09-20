import logging

import requests

from .models import Task
from .serializers import TaskSerializer
from .utils import handle_exception

logger = logging.getLogger(__name__)


def callback(task: Task, action: str) -> None:
    url = task.callback
    if not url:
        return
    json = TaskSerializer(instance=task)
    message = dict(action=action, task=json.data)
    print(message)
    try:
        resp = requests.post(url, json=message)
        resp.raise_for_status()
        return resp
    except Exception as exc:
        logger.error(f"Error posting data to callback URL: {url}")
        handle_exception(exc)
