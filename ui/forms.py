from django import forms

from task.models import Task
from task.utils import parse_shared_link


class NewTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["shared_link", "shared_id", "shared_password", "full_download_now"]
        widgets = {
            "shared_link": forms.TextInput(
                attrs={"class": "input input-bordered w-full max-w-xxs"},
            ),
            "shared_password": forms.TextInput(
                attrs={"class": "input input-bordered w-full max-w-xxs"},
            ),
            "full_download_now": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        shared_link = cleaned_data.get("shared_link")
        if not shared_link:
            return cleaned_data
        try:
            link = parse_shared_link(shared_link)
        except ValueError as e:
            self.add_error("shared_link", str(e))
            return cleaned_data
        cleaned_data["shared_id"] = link["id"]
        if not cleaned_data["shared_password"] and link["password"]:
            cleaned_data["shared_password"] = link["password"]
