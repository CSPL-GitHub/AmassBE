from order.models import OrderPayment, LoyaltyProgramSettings, LoyaltyPointsCreditHistory
from order.models import Order, Customer
from koms.models import Order as KOMSOrder
from core.models import Vendor, Platform
from inventory.models import InventorySyncErrorLog
from inventory.utils import sync_order_content_with_inventory
from core.PLATFORM_INTEGRATION.woocommerce_ecom import WooCommerce
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
import requests


class LoyaltyPointsSyncError(Exception):
    pass


@receiver(post_save, sender=Order)
def create_loyalty_points_credit_history(sender, instance, created, **kwargs):
    if (instance.customerId.FirstName != "Guest") and (instance.customerId.Phone_Number != "0"):
        if instance.Status == 2:
            try:
                vendor_instance = Vendor.objects.get(pk=instance.vendorId.pk)
                loyalty_settings = LoyaltyProgramSettings.objects.get(vendor=vendor_instance.pk)

                if loyalty_settings.is_active == True:
                    customer_instance = Customer.objects.get(pk=instance.customerId.pk)
                    koms_order = KOMSOrder.objects.get(master_order=instance.pk)
                    order_payment = OrderPayment.objects.filter(orderId=instance.pk, status=True).last()

                    if (koms_order.order_status == 10) and (order_payment.status == True):
                        if loyalty_settings.redeem_limit_applied_on == "subtotal":
                            credit_points = round(instance.subtotal / loyalty_settings.amount_spent_in_rupees_to_earn_unit_point)

                        elif loyalty_settings.redeem_limit_applied_on == "final_total":
                            credit_points = round(instance.TotalAmount / loyalty_settings.amount_spent_in_rupees_to_earn_unit_point)

                        expiry_date = timezone.now() + timedelta(days=loyalty_settings.points_expiry_days)

                        credit_history_instance = LoyaltyPointsCreditHistory.objects.create(
                            customer=customer_instance,
                            order=instance,
                            points_credited=credit_points,
                            expiry_date=expiry_date,
                            is_expired=False,
                            total_points_redeemed=0,
                            balance_points=credit_points,
                            vendor=vendor_instance
                        )

                        if credit_history_instance:
                            existing_points_balance = customer_instance.loyalty_points_balance
                            customer_instance.loyalty_points_balance = existing_points_balance + credit_history_instance.points_credited
                            customer_instance.save()

                        # WooCommerce syncing
                        # woocommerce_platform = Platform.objects.filter(VendorId=instance.vendorId, Name="WooCommerce", isActive=True).first()

                        # if woocommerce_platform:
                        #     woocommerce_customer_details = WooCommerce.get_customer_by_phone_number(customer_instance.Phone_Number, instance.vendorId)

                        #     if woocommerce_customer_details.status_code == 404:
                        #         pass

                        #     elif woocommerce_customer_details and woocommerce_customer_details.status_code == 200:
                        #         woocommerce_customer_details = woocommerce_customer_details.json()

                        #         if woocommerce_customer_details.get('id'):
                        #             balance_update_response = WooCommerce.update_loyalty_points_balance_of_customer(
                        #                 woocommerce_customer_details.get('id'),
                        #                 customer_instance.loyalty_points_balance,
                        #                 instance.vendorId
                        #             )

                        #             if balance_update_response == True:
                        #                 pass
                        #                 # notify(type=3, msg='0', desc='Loyalty points synced', stn=['POS'], vendorId=vendor_id)

                        #             else:
                        #                 raise LoyaltyPointsSyncError("Points not synced")

                        #     else:
                        #         raise LoyaltyPointsSyncError("Points not synced")

            except Exception as e:
                print("create_loyalty_points_credit_history Signal:\n", e)


@receiver(post_save, sender=Order)
def sync_order_to_inventory(sender, instance, **kwargs):
    vendor_instance = Vendor.objects.filter(pk=instance.vendorId.pk).first()

    platform = Platform.objects.filter(Name="Inventory", isActive=True, VendorId=instance.vendorId.pk).first()

    if platform:
        if instance.Status == 3:
            sync_order_content_with_inventory(instance.pk, instance.vendorId.pk)

        elif instance.Status == 2:
            sync_order_content_with_inventory(instance.pk, instance.vendorId.pk)

            try:
                base_url = platform.baseUrl

                odoo_order_json_post_url = f"{base_url}api/confirm_order/"

                request_data = {
                    "jsonrpc": "2.0",
                    "params": {
                        "order_id": instance.pk,
                        "vendor_id": instance.vendorId.pk,
                    }
                }

                confirm_order_response = requests.post(odoo_order_json_post_url, json=request_data)

                confirm_order_response_data = confirm_order_response.json()
                
                if (confirm_order_response.status_code != 200) or \
                ((confirm_order_response.status_code == 200) and (confirm_order_response_data.get("result").get("success") == False)):
                    inventory_sync_error_log_instance = InventorySyncErrorLog(
                        payload=request_data,
                        response_status_code=confirm_order_response_data.status_code,
                        response=confirm_order_response_data.get("result").get("message"),
                        vendor=vendor_instance
                    )

                    inventory_sync_error_log_instance.save()

            except Exception as e:
                inventory_sync_error_log_instance = InventorySyncErrorLog(
                    payload="",
                    response_status_code=0,
                    response=str(e),
                    vendor=vendor_instance
                )

                inventory_sync_error_log_instance.save()
