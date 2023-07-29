from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("new", views.new_task, name="new_task"),
    path("list", views.task_list, name="task_list"),
    path("nothing", views.nothing, name="nothing"),
]
