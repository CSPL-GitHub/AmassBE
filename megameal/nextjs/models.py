from django.db import models
from core.models import Vendor
from order.models import Customer
from uuid import uuid4


class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to="user_profile", max_length=1000, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    token = models.UUIDField(default=uuid4, editable=False, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    Customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
