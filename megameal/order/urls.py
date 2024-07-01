"""megameal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from .views import *
from django.views.generic import TemplateView

urlpatterns = [
    path('openOrder/',openOrder,name="openOrder"),
    path('addLineItem/',addLineItem,name='addLineItem'),
    path('addModifier/',addModifier,name='addModifier'), #not used yet
    path('applyDiscount/',applyDiscount,name='applyDiscount'), 
    path('payBill/',payBill,name='payBill'), #not used yet
    path('updateOrderStatusFromKOMS/',updateOrderStatusFromKOMS,name='updateOrderStatusFromKOMS'), #not used now
    path('womsCreateOrder/',womsCreateOrder,name='womsCreateOrder'), #not used now
    path('loyaltypointscredit/', create_loyalty_points_credit_history), # for testing purpose
    path('completeorder/', complete_order), # for testing purpose
    path('change_customer_id_of_order/', change_customer_id_of_order)
]
