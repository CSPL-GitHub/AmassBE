from django.db import models
from core.models import Vendor


class InventorySyncErrorLog(models.Model):
    payload = models.JSONField()
    response_status_code = models.IntegerField()
    response = models.TextField()
    request_datetime = models.DateTimeField(auto_now_add=True)
    is_synced = models.BooleanField(default=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_inventory_sync_error_log")
