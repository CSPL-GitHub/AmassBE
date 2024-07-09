from django.contrib import admin
from .models import *


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    
    list_display = ('pk','customerId','TotalAmount','vendorId',)
    list_filter = ('vendorId',)
    search_fields = ('pk','vendorId__Name')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    
    list_display = ('FirstName','LastName','Email','Phone_Number','VendorId',)
    list_filter = ('VendorId',)
    search_fields = ('FirstName','LastName','VendorId__Name','Email')
    # show_facets = admin.ShowFacets.ALWAYS

@admin.register(Order_Discount)
class Order_DiscountAdmin(admin.ModelAdmin):
    
    list_display = ('discountName','discountCode','is_active','vendorId',)
    list_filter = ('vendorId',)
    search_fields = ('discountName','discountCode','vendorId__Name')
    # show_facets = admin.ShowFacets.ALWAYS

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    
    list_display = ('customer', 'is_selected',)
    list_filter = ('customer', 'is_selected',)
    search_fields = ('customer__FirstName',)
    # show_facets = admin.ShowFacets.ALWAYS
    
    
@admin.register(LoyaltyPointsCreditHistory)
class LoyaltyPointsCreditHistoryAdmin(admin.ModelAdmin):
    
    list_display = ( 'order','customer','vendor')
    list_filter = ('customer', 'order',)
    search_fields = ('customer__FirstName',)
    # show_facets = admin.ShowFacets.ALWAYS
    
    
@admin.register(LoyaltyProgramSettings)
class LoyaltyProgramSettingsAdmin(admin.ModelAdmin):
    
    list_display = ('vendor','amount_spent_in_rupees_to_earn_unit_point', 'unit_point_value_in_rupees','points_expiry_days','is_active')
    # show_facets = admin.ShowFacets.ALWAYS
    
    
admin.site.register(LoyaltyPointsRedeemHistory)
