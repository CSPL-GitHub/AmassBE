from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings



admin.site.site_header = "MegaMeal Admin Panel"


urlpatterns = [
    path('admin/', admin.site.urls),
    # path('',include('useradmin.urls')),
    path('kiosk/',include('kiosk.urls')),
    path('order/',include('order.urls')), 
    path('koms/',include('koms.urls')),
    path('woms/',include('woms.urls')),
    path('realtime/', include('realtime.urls')),
    path('pos/',include('pos.urls')),
    path('nextjs/',include('nextjs.urls')),
    path('inventory/',include('inventory.urls')),
    path('sop/',include('sop.urls')),
    # path('media/', static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)),
]

urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
