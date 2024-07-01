from django.urls import path
from .views import *
from django.views.generic import TemplateView

urlpatterns = [
    path('squareMenuWebhook/<int:vendorId>',squareMenuWebhook,name='squareMenuWebhook'),
    path('wooComerceOrderWebhook/<int:vendorId>',wooComerceOrderWebhook,name='wooComerceOrderWebhook'),
    path('wooComerceOrderUpdateWebhook/<int:vendorId>',wooComerceOrderUpdateWebhook,name='wooComerceOrderUpdateWebhook'),
    path('squareOrderWebhook/<int:vendorId>',squareOrderWebhook,name='squareOrderWebhook'),
    path('RazorPayUpdate/',RazorPayUpdate,name='RazorPayUpdate'), #not used in now
    path('create_customer_webhook/', create_customer_webhook, name='create_customer_webhook'),
    path('update_customer_webhook/', update_customer_webhook, name='update_customer_webhook')
]