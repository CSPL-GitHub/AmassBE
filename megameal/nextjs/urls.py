from django.urls import path ,include
from . import views
from rest_framework.routers import DefaultRouter


router = DefaultRouter()

router.register("setting/user", views.userViewSet, basename="nextjs")

urlpatterns = [
      path('', include(router.urls)),
      path('login/',views.login), # Login api for web
      path('register/',views.register), # Register api for web
      path('updateUser/',views.updateUser), # Update user  api for web
      path('check_order/',views.check_order_items_status, name="check_order"),
      path('CreateOrder/',views.CreateOrder), # Create order  api for web
      path('CreateOrderApp/',views.CreateOrderApp), # Create order  api for web
      path('getOrderData/',views.getOrderData), # Get order data api for web
      path('get_timings/',views.get_timings), 
      path('get_customer_address/',views.get_customer_address), # Get address   api for web
      path('set_customer_address/',views.set_customer_address), # Create address order  api for web
      path('delete_customer_address/',views.delete_customer_address), # Delete address order  api for web
      path('select_address/',views.select_address), # select address order  api for web
      path('getTags/',views.getTags), # get vendor tags
      path('get_points/',views.get_points), # get_points
      path('verify_address/',views.verify_address), # verify_address by destination
      path('get_banner/', views.get_banner, name='get_banner'),
      path('get_header_footer_section/', views.get_header_footer_section, name='get_header_footer_section'),
      path('get_homepage_content/', views.get_homepage_content, name='get_homepage_content'),
]
