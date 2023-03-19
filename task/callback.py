import logging

import requests

from .serializers import TaskSerializer
from .utils import handle_exception

logger = logging.getLogger(__name__)


def callback(task, action):
    url = task.callback
    json = TaskSerializer(instance=task)
    message = dict(action=action, task=json.data)
    print(message)
    try:
        resp = requests.post(url, json=message)
        resp.raise_for_status()
        return resp
    except Exception as exc:
        logger.error(f"Error posting data to callbak URL: {url}")
        handle_exception(task, exc)
