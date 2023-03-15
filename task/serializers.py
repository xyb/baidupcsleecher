from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "path",
            "sample_path",
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
        ]
