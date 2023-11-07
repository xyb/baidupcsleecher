import os
import shutil
from pathlib import Path
from typing import List

from django.conf import settings

from .models import Task


def purge(move_to_dir: Path = None) -> None:
    keep_dirs = set()
    for task in Task.objects.all():
        keep_dirs.add(task.data_path)
        keep_dirs.add(task.sample_data_path)

    exist_dirs = set()
    root = settings.DATA_DIR
    if root.exists():
        for dir in os.listdir(root):
            path = root / dir
            if path.is_dir() and len(dir.split(".")) in [2, 3]:
                exist_dirs.add(root / dir)

    useless = exist_dirs - keep_dirs
    print(f"{len(useless)} directories to be deleted.")

    for dir in sorted(useless):
        if not dir.exists():
            print(f"{dir} is not exists, skip deletion.")
            continue
        if move_to_dir:
            print(f"start move {dir} to trash dir {move_to_dir} ...")
            to_dir = move_to_dir / dir.name
            to_dir.parent.mkdir(parents=True, exist_ok=True)
            os.rename(dir, move_to_dir / dir.name)
            print(f"{dir} moved to trash dir.")
        else:
            print(f"start delete {dir} ...")
            shutil.rmtree(dir)
            print(f"{dir} deleted.")


def remove_tasks(keep_task_ids: List[int] = []) -> List[int]:
    if keep_task_ids:
        to_remove = Task.objects.exclude(id__in=keep_task_ids)
        to_remove.delete()
    return Task.objects.all().values_list("id", flat=True)
