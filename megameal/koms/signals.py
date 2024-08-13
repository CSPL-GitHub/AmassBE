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

        # OneSignal
        # from nextjs.push_notification import send_push_notification
        # response = send_push_notification(['a11797c8-ded9-46ca-b95c-6b586807de84',], "Order is ready", "Order ID")
        # print(response)

        # FCM
        # from pyfcm import FCMNotification
        # device_token = instance.customerId.device_token
        
        # fcm = FCMNotification(
        #     service_account_file="/home/megameal/dev/megameal/megameal/nextjs/megameal-7f6c9-firebase-adminsdk-pzzb8-65f0140314.json",
        #     project_id="megameal-7f6c9"
        # )
        
        # notification_title = "Order is ready"
        # notification_body = f"Your order #{instance.id} is ready for dispatch."

        # result = fcm.notify(
        #     fcm_token=device_token,
        #     notification_title=notification_title,
        #     notification_body=notification_body,
        # )
       
        # print(result)
