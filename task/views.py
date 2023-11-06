import logging
from io import BytesIO
from typing import Any

from baidupcs_py.baidupcs import BaiduPCSError
from django.http import HttpRequest
from django.http import HttpResponse
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.decorators import renderer_classes
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from .baidupcs import get_baidupcs_client
from .leecher import transfer
from .models import Task
from .serializers import CaptchaCodeSerializer
from .serializers import ErrorSerializer
from .serializers import FullDownloadNowSerializer
from .serializers import OperationSerializer
from .serializers import TaskSerializer

logger = logging.getLogger(__name__)


class JPEGRenderer(BaseRenderer):
    media_type = "image/jpeg"
    format = "jpg"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def delete_remote_files(
    remote_path: str,
    catch_error: bool = True,
) -> HttpResponse:
    try:
        client = get_baidupcs_client()
        if client.exists(remote_path):
            client.delete(remote_path)
    except Exception as exc:
        if catch_error:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            raise exc
    return Response(status=status.HTTP_204_NO_CONTENT)


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
    filterset_fields = ("shared_link", "shared_id", "status", "failed")

    @extend_schema(
        description="Remove remote files",
        responses={204: None, 404: None},
        methods=["DELETE"],
    )
    @extend_schema(
        description="List remote files",
        methods=["GET"],
    )
    @action(methods=["get", "delete"], detail=True, name="Remote Files")
    def files(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        task = self.get_object()
        if request.method == "GET":
            return Response(task.load_files())
        if request.method == "DELETE":
            return delete_remote_files(task.remote_path)

    @action(methods=["get", "delete"], detail=True, name="Local Files")
    def local_files(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        task = self.get_object()
        if request.method == "GET":
            return Response(task.list_local_files())
        if request.method == "DELETE":
            task.delete_files()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={200: bytes, 404: None})
    @action(detail=True, name="Captch Image")
    @renderer_classes([JPEGRenderer])
    def captcha(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        task = self.get_object()
        return HttpResponse(BytesIO(task.captcha), content_type=JPEGRenderer.media_type)

    @extend_schema(responses={200: TaskSerializer, 400: ErrorSerializer, 404: None})
    @action(methods=["post"], detail=True, name="Input Captcha Code")
    def captcha_code(self, request: HttpRequest, pk: int = None) -> HttpResponse:
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

    @action(methods=["post"], detail=True, name="Approve to download whole files")
    def full_download_now(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        serializer = FullDownloadNowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = self.get_object()
        task.full_download_now = serializer.validated_data["full_download_now"]
        task.save()
        return Response(TaskSerializer(task).data)

    @action(methods=["post"], detail=True, name="Restart task to downloading files")
    def restart_downloading(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        task = self.get_object()
        task.restart_downloading()
        return Response({"status": task.status})

    @action(methods=["post"], detail=True, name="Restart task from inited status")
    def restart(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        task = self.get_object()
        task.restart()
        return Response({"status": task.status})

    @action(methods=["post"], detail=True, name="Resume failed task")
    def resume(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        task = self.get_object()
        task.schedule_resume()
        return Response({"status": task.status})

    @extend_schema(responses={204: None, 400: ErrorSerializer, 404: None})
    @action(methods=["delete"], detail=True, name="Erase task, remote and local files")
    def erase(self, request: HttpRequest, pk: int = None) -> HttpResponse:
        task = self.get_object()
        task.erase()
        try:
            return delete_remote_files(task.remote_path, catch_error=False)
        except BaiduPCSError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer(self, *args: Any, **kwargs: Any) -> Serializer:
        if self.action == "captcha_code":
            return CaptchaCodeSerializer(*args, **kwargs)
        if self.action == "full_download_now":
            return FullDownloadNowSerializer(*args, **kwargs)
        if self.action in ["restart", "restart_downloading", "resume", "erase"]:
            return OperationSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)
