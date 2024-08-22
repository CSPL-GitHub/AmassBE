from rest_framework.response import Response
from rest_framework.decorators import api_view
from order.models import Order, Customer, OrderPayment, LoyaltyProgramSettings, LoyaltyPointsCreditHistory
from core.models import Vendor
from koms.models import Order as KOMSOrder
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
import json



# For testing purpose of create_loyalty_points_credit_history signal
@api_view(['POST'])
def create_loyalty_points_credit_history(request):
    data = request.data
    master_id = data['id']

    master_order_instance = Order.objects.get(pk=master_id)

    if (master_order_instance.customerId.FirstName != "Guest") and (master_order_instance.customerId.Phone_Number != "0"):
        if master_order_instance.Status == 2:
            try:
                loyalty_settings = LoyaltyProgramSettings.objects.get(vendor=vendor_instance.pk)

                if loyalty_settings.is_active == True:
                    vendor_instance = Vendor.objects.get(pk=master_order_instance.vendorId.pk)
                    customer_instance = Customer.objects.get(pk=master_order_instance.customerId.pk)
                    koms_order = KOMSOrder.objects.get(master_order=master_order_instance.pk)
                    order_payment = OrderPayment.objects.get(orderId=master_order_instance.pk, status=True)

                    if koms_order.order_status == 10 and order_payment.status:
                        credit_points = int(master_order_instance.subtotal / loyalty_settings.amount_spent_in_rupees_to_earn_unit_point)

                        expiry_date = timezone.now() + timedelta(days=loyalty_settings.points_expiry_days)

                        credit_history_instance = LoyaltyPointsCreditHistory.objects.create(
                            customer=customer_instance,
                            order=master_order_instance,
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

                        return Response("Points credited", status=201)
                    
                    else:
                        return Response("Payment not done or order not closed", status=400)

            except Exception as e:
                return Response(f"{e}", status=400)
        
        else:
            return Response("Order not complete", status=400)
        

# For testing purpose of create_loyalty_points_credit_history signal
@api_view(['POST'])
def complete_order(request):
    data = json.loads(request.body)
    
    master_id = data.get('master_id')
    staging_id = data.get('staging_id')
    payment_id = data.get('payment_id')

    master_order_instance = Order.objects.get(pk=master_id)
    koms_order_instance = KOMSOrder.objects.get(pk=staging_id)
    payment_instance = OrderPayment.objects.get(pk=payment_id)

    master_order_instance.Status = 2
    master_order_instance.save()

    koms_order_instance.order_status = 10
    koms_order_instance.save()

    payment_instance.status = True
    payment_instance.save()

    return Response(status=200)


@api_view(['PUT'])
def change_customer_id_of_order(request):
    body_data = request.data

    vendor_id = body_data.get('vendor_id')
    customer_id = body_data.get('customer_id')
    order_id = body_data.get('order_id')

    if not all((vendor_id, customer_id, order_id)):
        return Response("Vendor ID, Customer ID or Order ID is empty", status=status.HTTP_400_BAD_REQUEST)

    try:
        vendor_id, customer_id, order_id = map(int, (vendor_id, customer_id, order_id))
    except ValueError:
        return Response("Invalid Vendor ID, Customer ID or Order ID", status=status.HTTP_400_BAD_REQUEST)

    vendor = Vendor.objects.filter(pk=vendor_id).first()
    customer = Customer.objects.filter(pk=customer_id).first()
    master_order = Order.objects.filter(pk=order_id).first()

    if not all((vendor, customer, master_order)):
        return Response("Vendor, Customer, or Order does not exist", status=status.HTTP_400_BAD_REQUEST)

    master_order.customerId = customer
    master_order.save()

    return Response("Order mapped to Customer", status=status.HTTP_200_OK)
