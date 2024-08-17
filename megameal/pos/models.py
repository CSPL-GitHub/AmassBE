from django.db import models
from core.models import Vendor, Platform
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, User



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


class Department(models.Model):
    name = models.CharField(max_length=150)
    name_locale = models.CharField(max_length=150, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_departments")

    class Meta:
        unique_together = ('name', 'vendor')

    def __str__(self):
        return self.name


class CoreUserCategory(Group):
    name_locale = models.CharField(max_length=150, null=True, blank=True)
    is_editable = models.BooleanField(default=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_user_categories")


class DeparmentAndCoreUserCategory(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    core_user_category = models.ForeignKey(CoreUserCategory, on_delete=models.CASCADE)
    is_core_category_active = models.BooleanField(default=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class CoreUser(User):
    phone_number = models.PositiveBigIntegerField()
    current_address = models.TextField(max_length=2000, null=True, blank=True)
    permanent_address = models.TextField(max_length=2000, null=True, blank=True)
    profile_picture = models.ImageField(upload_to="user", max_length=500, null=True, blank=True)
    document_1 = models.ImageField(upload_to="user/document", max_length=500, null=True, blank=True)
    document_2 = models.ImageField(upload_to="user/document", max_length=500, null=True, blank=True)
    is_head = models.BooleanField(default=False)
    reports_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_reports_to')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_users")

    class Meta:
        unique_together = ('phone_number', 'vendor')


class POSPermission(models.Model):
    show_dashboard = models.BooleanField(default=False)
    show_tables_page = models.BooleanField(default=False)
    show_place_order_page = models.BooleanField(default=False)
    show_order_history_page = models.BooleanField(default=False)
    show_product_menu = models.BooleanField(default=False)
    show_store_time_setting = models.BooleanField(default=False)
    show_tax_setting = models.BooleanField(default=False)
    show_delivery_charge_setting = models.BooleanField(default=False)
    show_loyalty_points_setting = models.BooleanField(default=False)
    show_cash_register_setting = models.BooleanField(default=False)
    show_customer_setting = models.BooleanField(default=False)
    show_printer_setting = models.BooleanField(default=False)
    show_payment_machine_setting = models.BooleanField(default=False)
    show_banner_setting = models.BooleanField(default=False)
    show_excel_file_setting = models.BooleanField(default=False)
    show_employee_setting = models.BooleanField(default=False)
    show_reports = models.BooleanField(default=False)
    show_sop = models.BooleanField(default=False)
    show_language_setting = models.BooleanField(default=False)
    core_user_category = models.ForeignKey(CoreUserCategory, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class CashRegister(models.Model):
    balance_while_store_opening = models.FloatField()
    balance_while_store_closing = models.FloatField(default=0.0)
    created_by = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="opening_cash_entered_by")
    created_at = models.DateTimeField(auto_now_add=True)
    edited_by = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="closing_cash_entered_by")
    edited_at = models.DateTimeField(auto_now=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_cash_register")
