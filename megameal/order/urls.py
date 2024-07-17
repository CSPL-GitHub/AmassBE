from django.urls import path
from .views import *



urlpatterns = [
    path('openOrder/',openOrder,name="openOrder"),
    path('addLineItem/',addLineItem,name='addLineItem'),
    # path('updateOrderStatusFromKOMS/',updateOrderStatusFromKOMS,name='updateOrderStatusFromKOMS'), #not used now
    # path('womsCreateOrder/',womsCreateOrder,name='womsCreateOrder'), #not used now
    path('loyaltypointscredit/', create_loyalty_points_credit_history), # for testing purpose
    path('completeorder/', complete_order), # for testing purpose
    path('change_customer_id_of_order/', change_customer_id_of_order)
]
