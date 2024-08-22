from django.urls import path
from .views import *



urlpatterns = [
    path('loyaltypointscredit/', create_loyalty_points_credit_history), # for testing purpose
    path('completeorder/', complete_order), # for testing purpose
    path('change_customer_id_of_order/', change_customer_id_of_order)
]
