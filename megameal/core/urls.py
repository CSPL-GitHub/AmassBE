from django.urls import path ,include
from .views import *
from django.urls import path, include
from django.views.generic import TemplateView


urlpatterns = [
   # path('wcapi/',woocommerce_api), 
   # path('wpapi2/',wordpress_api2),
   # path('mult/',multithroding_api),
   path('syncMenuToAllChannels/',sync_menu_to_all_channels),
   path('pullMenuFromPos/',pull_menu_from_pos),
   path('excel_file_upload/', excel_file, name="file_upload"),
]
