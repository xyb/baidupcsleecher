from rest_framework import serializers

from .models import Task
from .utils import get_url_query


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
            "captcha_required",
            "captcha",
        ]

    def validate(self, data):
        shared_password = data.get('shared_password')
        query_pwd = get_url_query(data['shared_link'], 'pwd')
        if query_pwd and not shared_password:
            data['shared_password'] = query_pwd
        return data
