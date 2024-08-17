from django.contrib import admin
from pos.models import *



@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'vendor',)
    list_filter = ('is_active', 'vendor')
    search_fields = ('name',)
    ordering = ('vendor', 'name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(CoreUserCategory)
class CoreUserCategoryAdmin(admin.ModelAdmin):
    fields = ('vendor', 'name', 'is_editable', 'permissions',)

    list_display = ('name', 'is_editable', 'vendor',)
    list_filter = ('vendor', 'is_editable',)
    search_fields = ('name',)
    ordering = ('vendor', 'name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(DepartmentAndCoreUserCategory)
class DepartmentAndCoreUserCategoryAdmin(admin.ModelAdmin):
    fields = ('vendor', 'department', 'core_user_category', 'is_core_category_active',)

    list_display = ('department', 'core_user_category', 'is_core_category_active', 'vendor',)
    list_filter = ('is_core_category_active', 'vendor',)
    search_fields = ('department__name', 'core_user_category__name', 'vendor__name')
    ordering = ('vendor', 'department', 'core_user_category',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(CoreUser)
class CoreUserAdmin(admin.ModelAdmin):
    fields = (
        'vendor', 'username', 'password', 'first_name', 'last_name', 'email', 'phone_number',
        'current_address', 'permanent_address', 'profile_picture', 'document_1', 'document_2',
        'is_active', 'is_head', 'reports_to', 'groups',
    )

    list_display = ('first_name', 'last_name', 'username', 'is_active', 'is_head', 'vendor',)
    list_filter = ('vendor', 'groups', 'is_head',)
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'current_address', 'permanent_address',)
    ordering = ('vendor', 'first_name',)
    # show_facets = admin.ShowFacets.ALWAYS


@admin.register(POSPermission)
class POSPermissionAdmin(admin.ModelAdmin):
    fields = (
        "vendor", "core_user_category", "show_dashboard", "show_tables_page", "show_place_order_page",
        "show_order_history_page", "show_product_menu", "show_store_time_setting", "show_tax_setting",
        "show_delivery_charge_setting", "show_loyalty_points_setting", "show_cash_register_setting",
        "show_customer_setting", "show_printer_setting", "show_payment_machine_setting", "show_banner_setting",
        "show_excel_file_setting", "show_employee_setting", "show_reports", "show_sop", "show_language_setting",  
    )

    list_display = ("core_user_category", "vendor",)
    list_filter = ("vendor",)
    search_fields = ("core_user_category__name", "vendor__name",)


@admin.register(POSSetting)
class POSSettingAdmin(admin.ModelAdmin):
    fields = ('vendor', 'store_status', 'delivery_kilometer_limit', 'delivery_charges_for_kilometer_limit')


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


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    fields = (
        "vendor", "balance_while_store_opening", "balance_while_store_closing",
        "created_by", "created_at", "edited_by", "edited_at",
    )

    readonly_fields = ("created_at", "edited_at",)

    list_display = ("created_at", "balance_while_store_opening", "balance_while_store_closing", "vendor",)
    list_filter = ("vendor",)
    search_fields = ("vendor__name",)
    ordering = ('vendor', '-created_at',)
