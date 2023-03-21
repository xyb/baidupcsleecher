import logging
from io import BytesIO
from json import loads

from django.http import HttpResponse
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .baidupcs import get_baidupcs_client
from .leecher import save_link
from .models import Task
from .serializers import TaskSerializer

logger = logging.getLogger(__name__)


class TaskViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Task.objects.all().order_by("-id")
    serializer_class = TaskSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ("shared_link", "status")

    @action(detail=True)
    def files(self, request, pk=None):
        task = self.get_object()
        if task.files:
            files = loads(task.files)
        else:
            files = []
        return Response(files)

    @action(detail=True)
    def captcha(self, request, pk=None):
        task = self.get_object()
        return HttpResponse(BytesIO(task.captcha), content_type="image/jpeg")

    @action(methods=["post"], detail=True)
    def captcha_code(self, request, pk=None):
        task = self.get_object()
        code = request.data["code"]
        task.captcha_code = code
        task.captcha_required = False
        task.save()
        logger.info(f"captcha code received: {code}")
        try:
            client = get_baidupcs_client()
            save_link(client, task)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TaskSerializer(task).data)
