from django.contrib import admin
from .models import *



admin.site.register(Vendor_Settings)
admin.site.register(Core_User)
admin.site.register(POS_Settings)


@admin.register(VendorType)
class VendorTypeAdmin(admin.ModelAdmin):
    fields = ('type',)

    list_display = ('type',)
    search_fields = ('type',)
    ordering = ('type',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    fields = (
        'vendor_type', 'is_active', 'Name', 'phone_number', 'Email', 'Password', 
        'address_line_1', 'address_line_2', 'city', 'state', 'country',
        'currency', 'currency_symbol', 'primary_language', 'secondary_language',
        'gst_number', 'contact_person_name', 'contact_person_phone_number',
    )

    list_display = ('pk', 'Name', 'phone_number', 'Email', 'is_active',)
    list_filter = ('is_active', 'vendor_type', 'state', 'city', )
    search_fields = ('Name', 'phone_number', 'Email', 'address_line_1', 'address_line_2', 'city', 'state', 'contact_person_name', 'contact_person_phone_number',)
    ordering = ('Name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    fields = ('VendorId', 'isActive', 'expiryDate', 'Name', 'Name_locale', 'className', 'orderActionType', 'baseUrl', 'secreateKey', 'secreatePass')
    
    list_display = ('Name', 'isActive', 'expiryDate', 'VendorId',)
    list_filter = ('Name', 'isActive', 'VendorId',)
    search_fields = ('Name',)
    ordering = ('VendorId', 'Name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    fields = (
        'vendorId', 'categoryStation', 'categoryName', 'categoryName_locale', 'categoryPLU',
        'categoryDescription', 'categoryDescription_locale', 'categoryImageUrl', 'is_active'
    )
    
    list_display = ('categoryName', 'categoryStation', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    list_select_related = ('categoryStation', 'vendorId',)
    search_fields = ('categoryName', 'categoryName_locale', 'categoryStation__station_name', 'categoryDescription', 'categoryDescription_locale',)
    ordering = ('vendorId', 'categoryName', 'categoryStation',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'productName', 'productName_locale', 'PLU', 'productDesc', 'productDesc_locale', 'productPrice', 'tag', 'preparationTime', 'active', 'is_displayed_online')
    
    list_display = ('productName', 'productPrice', 'tag', 'active', 'vendorId',)
    list_filter = ('active', 'tag', 'is_displayed_online', 'vendorId',)
    search_fields = ('productName', 'productName_locale', 'productDesc', 'productDesc_locale',)
    ordering = ('vendorId', 'productName',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductCategoryJoint)
class ProductCategoryJointAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'category', 'product')
    
    list_display = ( 'product','category', 'vendorId',)
    list_filter = ('vendorId',)
    search_fields = ('category__Name', 'category__categoryDescription', 'product__productName', 'product__productDesc',)
    ordering = ('vendorId', 'category', 'product')
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductModifierGroup)
class ProductModifierGroupAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'name', 'name_locale', 'PLU', 'modifier_group_description', 'modifier_group_description_locale', 'min', 'max', 'active')
    
    list_display = ('name', 'min', 'max', 'active', 'vendorId',)
    list_filter = ('active', 'vendorId',)
    search_fields = ('name', 'name_locale', 'modifier_group_description', 'modifier_group_description_locale',)
    ordering = ('vendorId', 'name', 'min', 'max',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductModifier)
class ProductModifierAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'modifierName', 'modifierName_locale', 'modifierPLU', 'modifierDesc', 'modifierDesc_locale', 'modifierImg', 'modifierPrice', 'active')
    
    list_display = ('modifierName', 'modifierPrice', 'active', 'vendorId',)
    list_filter = ('active', 'vendorId',)
    search_fields = ('modifierName', 'modifierName_locale', 'modifierDesc', 'modifierDesc_locale',)
    ordering = ('vendorId', 'modifierName', 'modifierPrice',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductModifierAndModifierGroupJoint)
class ProductModifierAndModifierGroupJointAdmin(admin.ModelAdmin):
    fields = ('vendor', 'modifierGroup', 'modifier',)
    
    list_display = ( 'modifier','modifierGroup', 'vendor',)
    list_filter = ('vendor',)
    search_fields = ('modifierGroup__name', 'modifierGroup__modifier_group_description', 'modifier__modifierName', 'modifier__modifierDesc',)
    ordering = ('vendor', 'modifierGroup', 'modifier',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductAndModifierGroupJoint)
class ProductAndModifierGroupJointAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'product', 'modifierGroup', 'active',)
    
    list_display = ('product', 'modifierGroup', 'active', 'vendorId',)
    list_filter = ('active', 'vendorId',)
    search_fields = ('product__productName', 'product__productDesc', 'modifierGroup__name', 'modifierGroup__modifier_group_description',)
    ordering = ('vendorId', 'product', 'modifierGroup',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'product', 'url',)
    
    list_display = ( 'product', 'url','vendorId',)
    list_filter = ('vendorId',)
    search_fields = ('product__productName', 'product__productDesc',)
    ordering = ('vendorId', 'product',)
    # show_facets = admin.ShowFacets.ALWAYS
    
    
@admin.register(Product_Tax)
class Product_TaxAdmin(admin.ModelAdmin):
    
    list_display = ( 'vendorId','name', 'percentage',)
    list_filter = ('name', 'vendorId',)
    search_fields = ('name',)
    # show_facets = admin.ShowFacets.ALWAYS
