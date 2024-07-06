from django.contrib import admin
from .models import *



admin.site.register(Api_Logs)
admin.site.register(Vendor_Settings)
admin.site.register(Core_User)
admin.site.register(POS_Settings)
admin.site.register(Product_Tax)


@admin.register(VendorType)
class VendorTypeAdmin(admin.ModelAdmin):
    required_languages = ('en', 'ar')
    fields = ('type', 'type_ar')
    
    list_display = ('type', 'type_ar')
    search_fields = ('type', 'type_ar')
    ordering = ('type',)
    # show_facets = admin.ShowFacets.ALWAYS

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    required_languages = ('en', 'ar')
    fields = (
        'vendor_type', 'Name', 'Name_ar', 'phone_number', 'Password', 'address_line_1', 'address_line_2',
        'city', 'state', 'country', 'gst_number', 'contact_person_name', 'contact_person_name_ar',
        'contact_person_phone_number', 'is_active',
    )
    
    list_display = ('id', 'Name', 'Name_ar', 'phone_number', 'Email', 'is_active',)
    list_filter = ('is_active', 'vendor_type', 'state', 'city', )
    search_fields = (
        'Name', 'Name_ar', 'phone_number', 'Email', 'address_line_1', 'address_line_2',
        'city', 'state', 'country', 'contact_person_name', 'contact_person_name_ar', 'contact_person_phone_number',
    )
    ordering = ('Name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    fields = (
        'VendorId', 'Name', 'Name_ar', 'isActive', 'expiryDate', 'corePlatformType', 'className', 'orderActionType',
        'baseUrl', 'secreateKey', 'secreatePass', 'APIKey', 'macId', 'pushMenuUrl', 'autoSyncMenu',
    )
    
    list_display = ('Name', 'expiryDate', 'isActive', 'VendorId',)
    list_filter = ('VendorId', 'Name', 'isActive',)
    search_fields = ('Name',)
    ordering = ('VendorId', 'Name', 'isActive',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    fields = (
        'vendorId', 'categoryStation', 'categoryName', 'categoryName_ar', 'categoryPLU',
        'categoryDescription', 'categoryDescription_ar', 'categoryImageUrl', 'is_active'
    )
    
    list_display = ('categoryName', 'categoryName_ar','categoryStation', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    list_select_related = ('categoryStation', 'vendorId',)
    search_fields = ('categoryName', 'categoryName_ar', 'categoryStation__station_name', 'categoryDescription', 'categoryDescription_ar',)
    ordering = ('vendorId', 'categoryName', 'categoryStation',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    fields = (
        'vendorId', 'productName', 'productName_ar', 'PLU', 'productDesc', 'productDesc_ar',
        'productPrice', 'tag', 'tag_ar', 'preparationTime', 'active', 'is_displayed_online'
    )
    
    list_display = ('productName', 'productName_ar', 'productPrice', 'tag', 'active', 'vendorId',)
    list_filter = ('active', 'tag', 'is_displayed_online', 'vendorId',)
    search_fields = ('productName', 'productName_ar', 'productDesc', 'productDesc_ar',)
    ordering = ('vendorId', 'productName',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductCategoryJoint)
class ProductCategoryJointAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'category', 'product')
    
    list_display = ('category', 'product', 'vendorId',)
    list_filter = ('vendorId',)
    search_fields = ('category__Name', 'category__categoryDescription', 'product__productName', 'product__productDesc',)
    ordering = ('vendorId', 'category', 'product')
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductModifierGroup)
class ProductModifierGroupAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'name', 'name_ar', 'PLU', 'modifier_group_description', 'modifier_group_description_ar', 'min', 'max', 'active')
    
    list_display = ('name', 'name_ar', 'min', 'max', 'active', 'vendorId',)
    list_filter = ('active', 'vendorId',)
    search_fields = ('name', 'name_ar', 'modifier_group_description', 'modifier_group_description_ar',)
    ordering = ('vendorId', 'name', 'min', 'max',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductModifier)
class ProductModifierAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'modifierName', 'modifierName_ar', 'modifierPLU', 'modifierDesc', 'modifierDesc_ar', 'modifierImg', 'modifierPrice', 'active')
    
    list_display = ('modifierName', 'modifierName_ar', 'modifierPrice', 'active', 'vendorId',)
    list_filter = ('active', 'vendorId',)
    search_fields = ('modifierName', 'modifierName_ar', 'modifierDesc', 'modifierDesc_ar',)
    ordering = ('vendorId', 'modifierName', 'modifierPrice',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductModifierAndModifierGroupJoint)
class ProductModifierAndModifierGroupJointAdmin(admin.ModelAdmin):
    fields = ('vendor', 'modifierGroup', 'modifier',)
    
    list_display = ('modifierGroup', 'modifier', 'vendor',)
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
    
    list_display = ('vendorId', 'product', 'url',)
    list_filter = ('vendorId',)
    search_fields = ('product__productName', 'product__productDesc',)
    ordering = ('vendorId', 'product',)
    # show_facets = admin.ShowFacets.ALWAYS
