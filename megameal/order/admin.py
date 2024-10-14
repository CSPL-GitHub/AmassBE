from django.contrib import admin
from .models import *


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    fields = (
        'vendorId', 'externalOrderId', 'OrderDate', 'platform', 'customerId', 'orderType',
        'Status', 'Notes', 'arrivalTime', 'subtotal', 'delivery_charge', 'tax', 'discount',
        'TotalAmount', 'due',
    )
    
    list_display = ('pk','masterOrder', 'customerId', 'TotalAmount', 'vendorId',)
    list_filter = ('vendorId', 'platform', 'orderType',)
    search_fields = ('pk', 'externalOrderId', 'vendorId__Name')


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
    fields = (
        'customer', 'type', 'is_selected', 'address_line1', 'address_line2',
        'city', 'state', 'country', 'zipcode',
    )
    
    list_display = ('customer', 'address_line1', 'is_selected',)
    list_filter = ('city', 'zipcode')
    search_fields = (
        'customer__FirstName', 'customer__LastName', 'customer__Phone_Number',
        'address_line1', 'address_line2', 'city', 'state', 'country', 'zipcode',
    )
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
    


@admin.register(OrderPayment)
class OrderPaymentAdmin(admin.ModelAdmin):
    list_display = ('pk','orderId','masterPaymentId','type','paid','status')

admin.site.register(LoyaltyPointsRedeemHistory)

@admin.register(SplitOrderItem)
class SplitOrderItemAdminView(admin.ModelAdmin):
    list_display = ('pk','order_id','order_content_id')