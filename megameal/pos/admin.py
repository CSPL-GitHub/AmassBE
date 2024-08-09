from django.contrib import admin
from pos.models import *


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name','vendor',)
    list_filter = ('name','vendor')
    search_fields = ('name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(CoreUserCategory)
class CoreUserCategoryAdmin(admin.ModelAdmin):
    fields = ('vendor', 'department', 'is_editable', 'name', 'permissions',)

    list_display = ('name', 'department', 'is_editable', 'vendor',)
    list_filter = ('vendor', 'department', 'is_editable',)
    search_fields = ('name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(CoreUser)
class CoreUserAdmin(admin.ModelAdmin):
    fields = (
        'vendor', 'is_active', 'is_head', 'reports_to', 'username', 'password', 'first_name', 'last_name', 'email',
        'phone_number', 'current_address', 'permanent_address', 'profile_picture', 'document_1', 'document_2', 'groups',
    )

    list_display = ('first_name', 'last_name', 'username', 'is_active', 'is_head', 'vendor',)
    list_filter = ('vendor', 'groups', 'is_head',)
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'current_address', 'permanent_address',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(POSSetting)
class POSSettingAdmin(admin.ModelAdmin):
    fields = ('vendor', 'store_status', 'delivery_kilometer_limit', 'delivery_charges_for_kilometer_limit')


@admin.register(POSMenu)
class POSMenuAdmin(admin.ModelAdmin):
    fields = ('vendor', 'is_sop_active',)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('image','platform_type','vendor','is_active',)
    list_filter = ('vendor','platform_type')
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(POSUser)
class PosUserAdmin(admin.ModelAdmin):
    list_display = ('name','username','password','vendor','is_active',)
    list_filter = ('is_active','vendor')
    search_fields = ('name','username')
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(StoreTiming)
class StoreTimingAdmin(admin.ModelAdmin):
    list_display = ('slot_identity','day','open_time','close_time','vendor','is_holiday','is_active',)
    list_filter = ('day','vendor','is_holiday','is_active',)
    search_fields = ('slot_identity','day')
    # show_facets = admin.ShowFacets.ALWAYS

