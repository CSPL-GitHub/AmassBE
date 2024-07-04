from django.contrib import admin
from .models import *



admin.site.register(KOMSOrderStatus)
admin.site.register(Order_content)
admin.site.register(Order)
admin.site.register(Staff)


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'isStation', 'station_name', 'station_name_ar', 'client_id', 'client_secrete', 'tag', 'color_code', 'key',)
    
    list_display = ('station_name', 'station_name_ar', 'isStation', 'vendorId',)
    list_filter = ('isStation', 'vendorId',)
    search_fields = ('station_name', 'station_name_ar',)
    ordering = ('vendorId', 'station_name', 'isStation',)
    # show_facets = admin.ShowFacets.ALWAYS
