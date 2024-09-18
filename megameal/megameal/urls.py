from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test, login_required
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView



admin.site.site_header = "MegaMeal Admin Panel"


def is_admin(user):
    return user.is_active and user.is_staff and user.is_superuser

# Restrict the API Docs to Super-admin users
admin_swagger_schema = login_required(user_passes_test(is_admin)(SpectacularAPIView.as_view()))
admin_swagger_view = login_required(user_passes_test(is_admin)(SpectacularSwaggerView.as_view(url_name='schema')))


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
    path('api/schema/', admin_swagger_schema, name='schema'),
    path('api/docs/', admin_swagger_view, name='swagger-ui'), # Route for Swagger UI
]

urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
