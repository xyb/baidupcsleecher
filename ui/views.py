import json

from django.core.paginator import Page
from django.core.paginator import Paginator
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django_htmx.middleware import HtmxDetails

from .forms import NewTaskForm
from task.models import Task


class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails


def get_task_list_page(request: HtmxHttpRequest) -> Page:
    tasks = Task.objects.all().order_by("-id")
    page_number = int(request.GET.get("page") or 1)
    per_page = int(request.GET.get("per_page") or 10)
    paginator = Paginator(tasks, per_page=per_page)
    page = paginator.get_page(page_number)
    return page


@require_GET
def index(request: HtmxHttpRequest) -> HttpResponse:
    page = get_task_list_page(request)
    return render(request, "ui/index.html", {"page": page, "form": NewTaskForm()})


@require_GET
def task_list(request: HtmxHttpRequest) -> HttpResponse:
    page = get_task_list_page(request)
    return render(request, "ui/task_list.html", {"page": page})


@require_POST
def new_task(request: HtmxHttpRequest) -> HttpResponse:
    form = NewTaskForm(request.POST)
    if not form.is_valid():
        if not request.htmx:
            return render(request, "ui/new_task_form.html", {"form": form})

        return HttpResponse(
            status=422,
            content=render(request, "ui/new_task_errors.html", {"form": form}),
        )

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


@require_GET
def nothing(request: HtmxHttpRequest) -> HttpResponse:
    return HttpResponse()
