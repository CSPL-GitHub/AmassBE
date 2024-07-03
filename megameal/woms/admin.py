from django.contrib import admin
from woms.models import Waiter, Floor



@admin.register(Waiter)
class WaiterAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'name', 'name_ar', 'username', 'password', 'phone_number', 'email', 'image', 'is_waiter_head', 'is_active',)
    
    list_display = ('name', 'name_ar', 'phone_number', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    search_fields = ('name', 'name_ar', 'phone_number', 'email', 'username',)
    ordering = ('vendorId', 'name', 'is_active',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'name', 'name_ar', 'is_active',)
    
    list_display = ('name', 'name_ar', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    search_fields = ('name', 'name_ar',)
    ordering = ('vendorId', 'name', 'is_active',)
    # show_facets = admin.ShowFacets.ALWAYS
