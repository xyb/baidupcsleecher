import logging
from io import BytesIO
from json import loads

from django.conf import settings
from django.http import HttpResponse
from django_filters import rest_framework as filters
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .baidupcs import get_baidupcs_client
from .leecher import transfer
from .models import Task
from .serializers import CaptchaCodeSerializer
from .serializers import FullDownloadNowSerializer
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        task.full_download_now = settings.FULL_DOWNLOAD_IMMEDIATELY
        task.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @action(detail=True)
    def files(self, request, pk=None):
        task = self.get_object()
        if task.files:
            files = loads(task.files)
        else:
            files = []
        return Response(files)

    @action(detail=True)
    def local_files(self, request, pk=None):
        task = self.get_object()
        return Response(task.list_local_files())

    @action(detail=True)
    def captcha(self, request, pk=None):
        task = self.get_object()
        return HttpResponse(BytesIO(task.captcha), content_type="image/jpeg")

    @action(methods=["post"], detail=True)
    def captcha_code(self, request, pk=None):
        serializer = CaptchaCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = self.get_object()
        if not task.is_waiting_for_captcha_code:
            return Response(
                {"error": "captcha_code not required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = request.data["code"]
        task.captcha_code = code
        task.captcha_required = False
        task.save()
        logger.info(f"captcha code received: {code}")
        try:
            client = get_baidupcs_client()
            transfer(client, task)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TaskSerializer(task).data)

    @action(methods=["post"], detail=True)
    def full_download_now(self, request, pk=None):
        serializer = FullDownloadNowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = self.get_object()
        task.full_download_now = serializer.validated_data["full_download_now"]
        task.save()
        return Response(TaskSerializer(task).data)

    @action(methods=["post"], detail=True)
    def restart_downloading(self, request, pk=None):
        task = self.get_object()
        task.restart_downloading()
        return Response({"status": task.status})

    @action(methods=["post"], detail=True)
    def restart(self, request, pk=None):
        task = self.get_object()
        task.restart()
        return Response({"status": task.status})

    def get_serializer(self, *args, **kwargs):
        if self.action == "captcha_code":
            return CaptchaCodeSerializer(*args, **kwargs)
        if self.action == "full_download_now":
            return FullDownloadNowSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)
