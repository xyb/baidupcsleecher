import json

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .forms import NewTaskForm
from task.models import Task


def get_task_list_page(request):
    tasks = Task.objects.all().order_by("-id")
    page_number = int(request.GET.get("page") or 1)
    per_page = int(request.GET.get("per_page") or 10)
    paginator = Paginator(tasks, per_page=per_page)
    page = paginator.get_page(page_number)
    return page


def index(request):
    page = get_task_list_page(request)
    return render(request, "ui/index.html", {"page": page, "form": NewTaskForm()})


def task_list(request):
    page = get_task_list_page(request)
    return render(request, "ui/task_list.html", {"page": page})


@require_POST
def new_task(request):
    form = NewTaskForm(request.POST)
    if not form.is_valid():
        if request.htmx:
            return HttpResponse(
                status=422,
                content=render(request, "ui/new_task_errors.html", {"form": form}),
            )
        else:
            return render(request, "ui/new_task_form.html", {"form": form})

    task = form.save()

    if not request.htmx:
        return HttpResponseRedirect("/ui/")

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


def nothing(request):
    return HttpResponse()
