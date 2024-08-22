from django.db.models.signals import post_save
from django.dispatch import receiver
from woms.models import Floor, HotelTable



@receiver(post_save, sender=Floor)
def update_hotel_table_status(sender, instance, **kwargs):
    tables = HotelTable.objects.filter(floor=instance)

    if instance.is_active == False:
        tables.update(status=5)
    else:
        tables.update(status=1)
