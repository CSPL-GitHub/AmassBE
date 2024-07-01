from django.db import models
from pos.models import Department, CoreUserCategory, CoreUser
from core.models import Vendor


class Question(models.Model):
    question_number = models.PositiveSmallIntegerField()
    question = models.CharField(max_length=1000)
    is_response_multiple = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="department_questions")
    staff_category = models.ForeignKey(CoreUserCategory, on_delete=models.CASCADE, related_name="question_staff_category")
    # responsible_person = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="responsible_person")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_questions")

    class Meta:
        unique_together = ('question_number', 'department', 'vendor')


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answer_questions")
    answer_sequence_number = models.PositiveSmallIntegerField()
    ui_element = models.CharField(max_length=100)
    caption = models.CharField(max_length=500)
    # answer = models.CharField(max_length=500)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_answers")


class FormResponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="form_questions")
    # expected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="expected_answer")
    # actual_answer = models.CharField(max_length=500)
    submitted_response = models.JSONField()
    submitted_by = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="submitted_by")
    remark = models.TextField(max_length=1000, blank=True)
    response_datetime = models.DateTimeField(auto_now_add=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="department_response")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_form_response")
