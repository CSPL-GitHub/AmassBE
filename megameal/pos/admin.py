from django.contrib import admin
from pos.models import *


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


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    
    list_display = ('name','vendor',)
    list_filter = ('name','vendor')
    search_fields = ('name',)
    # show_facets = admin.ShowFacets.ALWAYS
    
    
admin.site.register(CoreUserCategory)
admin.site.register(CoreUser)
admin.site.register(POSSetting)
