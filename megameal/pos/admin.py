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
    list_filter = ("vendor", "core_user_category__department",)
    search_fields = ("core_user_category__name", "core_user_category__department__name", "vendor__name",)


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

    list_display = ("balance_while_store_opening", "balance_while_store_closing", "vendor",)
    list_filter = ("vendor",)
    search_fields = ("vendor__name",)
