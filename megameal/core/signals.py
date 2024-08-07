from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Vendor, Platform



@receiver(post_save, sender=Vendor)
def deactivate_related_platforms(sender, instance, **kwargs):
    if instance.is_active == False:
        related_platforms = Platform.objects.filter(VendorId=instance)
        related_platforms.update(isActive=False)
