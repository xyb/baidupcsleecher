import json

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from .forms import TaskForm
from task.models import Task


def index(request):
    return render(request, "ui/index.html")


def task_list(request):
    tasks = Task.objects.all().order_by("-id")
    page_number = int(request.GET.get("page") or 1)
    per_page = int(request.GET.get("per_page") or 10)
    paginator = Paginator(tasks, per_page=per_page)
    page = paginator.get_page(page_number)
    return render(request, "ui/task_list.html", {"page": page})


def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps(
                        {
                            "taskListChanged": None,
                            "showMessage": f"{task.id} added.",
                        },
                    ),
                },
            )
    else:
        form = TaskForm()
    return render(request, "ui/task_form.html", {"form": form})
