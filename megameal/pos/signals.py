from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Vendor
from pos.models import CoreUser, Department, CoreUserCategory



@receiver(post_save, sender=Vendor)
def deactivate_related_users(sender, instance, **kwargs):
    # To avoid signal firing during bulk operations
    if not kwargs.get('raw', False):
        if instance.is_active == False:
            related_users = CoreUser.objects.filter(vendor = instance.pk)

            related_users.update(is_active = False)


# @receiver(post_save, sender=Department)
# def deactivate_related_core_users_and_their_categories(sender, instance, **kwargs):
#     if not kwargs.get('raw', False):
#         if instance.is_active == False:
#             vendor_id = instance.vendor.pk

#             related_core_user_categories = CoreUserCategory.objects.filter(department=instance.pk, vendor=vendor_id)

#             related_core_user_categories.update(is_active = False)

#             related_core_user_category_ids = related_core_user_categories.values_list("pk", flat=True)

#             related_core_users = CoreUser.objects.filter(core_user_category__in = related_core_user_category_ids, vendor=vendor_id)

#             related_core_users.update(is_active = False)