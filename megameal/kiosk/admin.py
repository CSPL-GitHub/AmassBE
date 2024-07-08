from django.contrib import admin
from .models import *

@admin.register(KioskDiscount)
class KioskDiscountAdmin(admin.ModelAdmin):
    
    list_display = ('discountDesc', 'discountCode',)
    list_filter = ('discountDesc', 'discountCode',)
    search_fields = ('discountDesc',)
    # show_facets = admin.ShowFacets.ALWAYS
    

