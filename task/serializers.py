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
            "failed",
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
        return data
