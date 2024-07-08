from django.contrib import admin
from .models import *
# Register your models here.

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    
    list_display = ('pk','master_order','order_status','vendorId',)
    list_filter = ('vendorId',)
    search_fields = ('order_status','vendorId__Name')
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    
    list_display = ('first_name','last_name','station_id','vendorId','is_active',)
    list_filter = ('vendorId','station_id')
    search_fields = ('first_name','vendorId__Name','station_id__station_name')
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Station)
class StationsAdmin(admin.ModelAdmin):
    
    list_display = ('station_name','client_id','client_secrete','vendorId','isStation',)
    list_filter = ('vendorId','isStation')
    search_fields = ('station_name','vendorId__Name')
    # show_facets = admin.ShowFacets.ALWAYS

