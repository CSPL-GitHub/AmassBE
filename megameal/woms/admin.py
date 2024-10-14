from django.contrib import admin
from woms.models import Waiter, Floor, HotelTable



@admin.register(Waiter)
class WaiterAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'name', 'name_locale', 'username', 'password', 'phone_number', 'email', 'image', 'is_waiter_head', 'is_active',)
    
    list_display = ('name', 'name_locale', 'phone_number', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    search_fields = ('name', 'name_locale', 'phone_number', 'email', 'username',)
    ordering = ('vendorId', 'name', 'is_active',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'name', 'name_locale', 'is_active',)
    
    list_display = ('name', 'name_locale', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    search_fields = ('name', 'name_locale',)
    ordering = ('vendorId', 'name', 'is_active',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(HotelTable)
class HotelTableAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'floor', 'tableNumber', 'tableCapacity', 'guestCount', 'status', 'waiterId')
    
    list_display = ('tableNumber', 'floor', 'tableCapacity', 'vendorId',)
    list_filter = ('floor', 'tableCapacity', 'status', 'vendorId',)
    search_fields = ('tableNumber',)
    ordering = ('vendorId', 'floor', 'tableNumber',)
    # show_facets = admin.ShowFacets.ALWAYS
