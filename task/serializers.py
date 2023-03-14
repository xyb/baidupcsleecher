from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "shared_link",
            "shared_password",
            "status",
            "created_at",
            "started_at",
            "finished_at",
            "failed",
            "message",
        ]
