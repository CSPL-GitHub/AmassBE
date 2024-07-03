from django.contrib import admin
from .models import *



admin.site.register(Hotal_Tables)
admin.site.register(Floor)


@admin.register(Waiter)
class WaiterAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'name', 'name_ar', 'username', 'password', 'phone_number', 'email', 'image', 'is_waiter_head', 'is_active',)
    
    list_display = ('name', 'name_ar', 'phone_number', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    search_fields = ('name', 'name_ar', 'phone_number', 'email', 'username',)
    ordering = ('vendorId', 'name', 'is_active',)
    # show_facets = admin.ShowFacets.ALWAYS
