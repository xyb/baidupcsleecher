import logging
from io import BytesIO

from baidupcs_py.baidupcs import BaiduPCSError
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
from .serializers import OperationSerializer
from .serializers import TaskSerializer

logger = logging.getLogger(__name__)


def delete_remote_files(
    task_id,
    remote_path,
    success_message,
    catch_error=True,
):
    try:
        client = get_baidupcs_client()
        client.delete(remote_path)
    except Exception as exc:
        if catch_error:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            raise exc
    return Response({task_id: success_message})


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

    @action(methods=["get", "delete"], detail=True, name="Remote Files")
    def files(self, request, pk=None):
        task = self.get_object()
        if request.method == "GET":
            return Response(task.load_files())
        if request.method == "DELETE":
            return delete_remote_files(
                task.id,
                task.remote_path,
                "remote files deleted",
            )

    @action(methods=["get", "delete"], detail=True, name="Local Files")
    def local_files(self, request, pk=None):
        task = self.get_object()
        if request.method == "GET":
            return Response(task.list_local_files())
        if request.method == "DELETE":
            task.delete_files()
            return Response({task.id: "local files deleted"})

    @action(detail=True, name="Captch Image")
    def captcha(self, request, pk=None):
        task = self.get_object()
        return HttpResponse(BytesIO(task.captcha), content_type="image/jpeg")

    @action(methods=["post"], detail=True, name="Input Captcha Code")
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

    @action(methods=["post"], detail=True, name="Approve to download whole files")
    def full_download_now(self, request, pk=None):
        serializer = FullDownloadNowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = self.get_object()
        task.full_download_now = serializer.validated_data["full_download_now"]
        task.save()
        return Response(TaskSerializer(task).data)

    @action(methods=["post"], detail=True, name="Restart task to downloading files")
    def restart_downloading(self, request, pk=None):
        task = self.get_object()
        task.restart_downloading()
        return Response({"status": task.status})

    @action(methods=["post"], detail=True, name="Restart task from inited status")
    def restart(self, request, pk=None):
        task = self.get_object()
        task.restart()
        return Response({"status": task.status})

    @action(methods=["post"], detail=True, name="Resume failed task")
    def resume(self, request, pk=None):
        task = self.get_object()
        task.schedule_resume()
        return Response({"status": task.status})

    @action(methods=["delete"], detail=True, name="Erase task, remote and local files")
    def erase(self, request, pk=None):
        task = self.get_object()
        task_id = task.id
        task.erase()
        message = "task deleted"
        try:
            return delete_remote_files(
                task_id,
                task.remote_path,
                message,
                catch_error=False,
            )
        except BaiduPCSError:
            return Response({task_id: message})

    def get_serializer(self, *args, **kwargs):
        if self.action == "captcha_code":
            return CaptchaCodeSerializer(*args, **kwargs)
        if self.action == "full_download_now":
            return FullDownloadNowSerializer(*args, **kwargs)
        if self.action in ["restart", "restart_downloading", "resume", "erase"]:
            return OperationSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)
