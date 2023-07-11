from django.conf import settings
from rest_framework import serializers

from .models import Task
from .utils import parse_shared_link


class TaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "path",
            "sample_path",
            "shared_id",
            "shared_link",
            "shared_password",
            "status",
            "callback",
            "created_at",
            "started_at",
            "finished_at",
            "transfer_completed_at",
            "file_listed_at",
            "sample_downloaded_at",
            "full_downloaded_at",
            "full_download_now",
            "total_files",
            "total_size",
            "largest_file",
            "largest_file_size",
            "done",
            "failed",
            "recoverable",
            "retry_times",
            "message",
            "captcha_required",
            "captcha_url",
            "captcha",
        ]

    def validate(self, data):
        shared_password = data.get("shared_password")
        link = parse_shared_link(data["shared_link"])
        data["shared_id"] = link["id"]
        if not shared_password and link["password"]:
            data["shared_password"] = link["password"]

        full_download_now = data.get("full_download_now")
        if full_download_now is None:
            data["full_download_now"] = settings.FULL_DOWNLOAD_IMMEDIATELY
        return data


class CaptchaCodeSerializer(serializers.Serializer):
    code = serializers.CharField()


class FullDownloadNowSerializer(serializers.Serializer):
    full_download_now = serializers.BooleanField()


class OperationSerializer(serializers.Serializer):
    pass
