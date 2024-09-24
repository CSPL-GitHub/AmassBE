from django.db import models
from pos.models import Department, CoreUserCategory, CoreUser
from core.models import Vendor



class Question(models.Model):
    question_number = models.PositiveSmallIntegerField()
    question = models.CharField(max_length=1000)
    question_locale = models.CharField(max_length=1000, null=True, blank=True)
    is_response_multiple = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="department_questions")
    staff_category = models.ForeignKey(CoreUserCategory, on_delete=models.CASCADE, related_name="question_staff_category")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_questions")

    class Meta:
        unique_together = ('question_number', 'department', 'vendor')

    def save(self, *args, **kwargs):
        if not self.question_locale:
            self.question_locale = self.question

        super().save(*args, **kwargs)
        
        return self


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answer_questions")
    answer_sequence_number = models.PositiveSmallIntegerField()
    ui_element = models.CharField(max_length=100)
    caption = models.CharField(max_length=500)
    caption_locale = models.CharField(max_length=500, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_answers")

    def save(self, *args, **kwargs):
        if not self.caption_locale:
            self.caption_locale = self.caption

        super().save(*args, **kwargs)
        
        return self


class FormResponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="form_questions")
    submitted_response = models.JSONField()
    submitted_by = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="submitted_by")
    remark = models.TextField(max_length=1000, null=True, blank=True)
    response_datetime = models.DateTimeField(auto_now_add=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="department_response")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_form_response")
