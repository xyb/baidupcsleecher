from django.core.paginator import Paginator
from django.shortcuts import render

from task.models import Task


def index(request):
    tasks = Task.objects.all().order_by("-id")

    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 10)
    paginator = Paginator(tasks, per_page=per_page)
    page = paginator.get_page(page_number)

    return render(request, "ui/index.html", {"page": page, "per_page": per_page})
