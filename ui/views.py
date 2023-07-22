import json

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .forms import TaskForm
from task.models import Task
from task.utils import parse_shared_link


def get_task_list_page(request):
    tasks = Task.objects.all().order_by("-id")
    page_number = int(request.GET.get("page") or 1)
    per_page = int(request.GET.get("per_page") or 10)
    paginator = Paginator(tasks, per_page=per_page)
    page = paginator.get_page(page_number)
    return page


def index(request):
    page = get_task_list_page(request)
    return render(request, "ui/index.html", {"page": page})


def task_list(request):
    page = get_task_list_page(request)
    return render(request, "ui/task_list.html", {"page": page})


def new_task(request):
    form = TaskForm()
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            link = parse_shared_link(task.shared_link)
            task.shared_id = link["id"]
            if not task.shared_password and link["password"]:
                task.shared_password = link["password"]
            task.save()

            if request.htmx:
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
                return HttpResponseRedirect("/ui/")
    return render(request, "ui/new_task_form.html", {"form": form})
