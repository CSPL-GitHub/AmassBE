from django.db import models
from core.models import Vendor,Platform
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError



def validate_phone_number_length(value):
    if len(str(value)) != 10:
        raise ValidationError("Phone number must be exactly 10 digits.")


class POSMenu(models.Model):
    is_sop_active = models.BooleanField(default=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    def __str__(self):
        return self.vendor.Name


class StoreTiming(models.Model):
    DAYS_OF_WEEK_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    slot_identity = models.CharField( max_length=50)
    day = models.CharField(max_length=50, choices=DAYS_OF_WEEK_CHOICES,)
    is_holiday = models.BooleanField( default=False)
    is_active = models.BooleanField( default=False)
    open_time = models.TimeField()
    close_time = models.TimeField()
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True, blank=True)
    

class POSUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    name =  models.CharField(max_length=100)
    phone_number = models.PositiveBigIntegerField()
    email = models.EmailField()
    is_active = models.BooleanField(default=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Banner(models.Model):
    image = models.URLField(max_length=200)
    is_active = models.BooleanField(default=True)
    platform_type = models.CharField(max_length=20, choices=(('website', 'website'), ('app', 'app'),), default='website')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class POSSetting(models.Model):
    store_status = models.BooleanField(default=False)
    delivery_kilometer_limit = models.IntegerField(default=5)
    delivery_charges_for_kilometer_limit = models.IntegerField(default=0)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    def __str__(self):
        return self.vendor.Name


class CoreUserCategory(Group):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_user_categories")


class CoreUser(User):
    phone_number = models.PositiveBigIntegerField(unique=True, validators=(validate_phone_number_length,))
    current_address = models.TextField(max_length=2000)
    permanent_address = models.TextField(max_length=2000)
    profile_picture = models.ImageField(upload_to="user_profile", max_length=500, blank=True, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_users")


class Department(models.Model):
    name = models.CharField(max_length=150)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_departments")

    class Meta:
        unique_together = ('name', 'vendor')



@receiver(post_save, sender=Vendor)
def deactivate_related_users(sender, instance, **kwargs):
    if not kwargs.get('raw', False):  # To avoid signal firing during bulk operations
        if instance.is_active is False:  # When is_active of Vendor changes to False
            related_users = POSUser.objects.filter(vendor=instance)
            related_users.update(is_active=False)