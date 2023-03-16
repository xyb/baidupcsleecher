from json import loads

from django_filters import rest_framework as filters
from rest_framework import generics, mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Task
from .serializers import TaskSerializer

class TaskViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Task.objects.all().order_by("-id")
    serializer_class = TaskSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ("shared_link", "status")

    @action(detail=True)
    def files(self, request, pk=None):
        task = self.get_object()
        return Response(loads(task.files))