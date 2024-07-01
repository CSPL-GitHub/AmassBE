from django.contrib import admin
from .models import *



@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'categoryStation', 'categoryName', 'categoryPLU', 'categoryDescription', 'categoryImageUrl', 'is_active')
    
    list_display = ('categoryName', 'categoryStation', 'is_active', 'vendorId',)
    list_filter = ('is_active', 'vendorId',)
    list_select_related = ('categoryStation', 'vendorId',)
    search_fields = ('categoryName', 'categoryStation__station_name', 'categoryDescription',)
    ordering = ('vendorId', 'categoryName', 'categoryStation',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'productName', 'PLU', 'productDesc', 'productPrice', 'tag', 'preparationTime', 'active', 'is_displayed_online')
    
    list_display = ('productName', 'productPrice', 'tag', 'active', 'vendorId',)
    list_filter = ('active', 'tag', 'is_displayed_online', 'vendorId',)
    search_fields = ('productName', 'productDesc',)
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
    fields = ('vendorId', 'name', 'PLU', 'modifier_group_description', 'min', 'max', 'active')
    
    list_display = ('name', 'min', 'max', 'active', 'vendorId',)
    list_filter = ('active', 'vendorId',)
    search_fields = ('name', 'modifier_group_description',)
    ordering = ('vendorId', 'name', 'min', 'max',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(ProductModifier)
class ProductModifierAdmin(admin.ModelAdmin):
    fields = ('vendorId', 'modifierName', 'modifierPLU', 'modifierDesc', 'modifierImg', 'modifierPrice', 'active')
    
    list_display = ('modifierName', 'modifierPrice', 'active', 'vendorId',)
    list_filter = ('active', 'vendorId',)
    search_fields = ('modifierName', 'modifierDesc',)
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



admin.site.register(Api_Logs)
admin.site.register(Vendor_Settings)
admin.site.register(Platform)
admin.site.register(Vendor)
admin.site.register(VendorType)
admin.site.register(Core_User)
admin.site.register(POS_Settings)
admin.site.register(Product_Tax)