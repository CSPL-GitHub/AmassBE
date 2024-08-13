from django.db.models.signals import post_save
from django.dispatch import receiver
from koms.models import Order, Order_tables
from woms.models import HotelTable, Waiter
from koms.views import notify



@receiver(post_save, sender=Order)
def send_complete_order_notification(sender, instance, **kwargs):
    if instance.order_status == 3:
        vendor_id = instance.vendorId.pk
        order_id = instance.master_order.pk

        order_tables = Order_tables.objects.filter(orderId=instance.pk).values_list("tableId", flat=True)

        tables = HotelTable.objects.filter(pk__in=order_tables, vendorId=vendor_id)

        for table in tables:
            if table.waiterId and (table.waiterId.is_waiter_head == False):
                notify(
                    type = 3,
                    msg = '0',
                    desc = f"Order No.{order_id} is ready",
                    stn = [f'WOMS{table.waiterId.pk}'],
                    vendorId = vendor_id
                )
        
        waiter_heads = Waiter.objects.filter(is_waiter_head=True, vendorId=vendor_id)

        if waiter_heads:
            for waiter_head in waiter_heads:
                notify(
                    type = 3,
                    msg = '0',
                    desc = f"Order No.{order_id} is ready",
                    stn = [f'WOMS{waiter_head.pk}'],
                    vendorId = vendor_id
                )
