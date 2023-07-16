from django import forms

from task.models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["shared_link", "shared_password", "full_download_now"]
        widgets = {
            "shared_link": forms.TextInput(attrs={"class": "form-control"}),
            "shared_password": forms.TextInput(attrs={"class": "form-control"}),
            "full_download_now": forms.TextInput(attrs={"class": "form-control"}),
        }
