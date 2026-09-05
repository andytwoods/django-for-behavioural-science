"""Forms for the study app.

A ``ModelForm`` builds an HTML form from a model. Django reads the model's fields, works
out a sensible widget and set of validation rules for each one, and renders them. The
admin does this too, behind the scenes; writing the form yourself is how you put one on a
page of your own, for people who don't have an admin login.
"""

from django import forms

from .models import Study


# --8<-- [start:study-form]
class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ["name", "slug", "code"]
# --8<-- [end:study-form]
