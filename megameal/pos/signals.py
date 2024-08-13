from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Vendor
from pos.models import POSUser, Department, DeparmentAndCoreUserCategory



@receiver(post_save, sender=Vendor)
def deactivate_related_users(sender, instance, **kwargs):
    if not kwargs.get('raw', False):  # To avoid signal firing during bulk operations
        if instance.is_active == False:
            related_users = POSUser.objects.filter(vendor=instance)

            related_users.update(is_active=False)


@receiver(post_save, sender=Department)
def deactivate_related_core_user_categories(sender, instance, **kwargs):
    # To avoid signal firing during bulk operations
    if not kwargs.get('raw', False):
        if instance.is_active == False:
            related_core_user_categories = DeparmentAndCoreUserCategory.objects.filter(department=instance, vendor=instance.vendor.pk)

            related_core_user_categories.update(is_core_category_active=False)