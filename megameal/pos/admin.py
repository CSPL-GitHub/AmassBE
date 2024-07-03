from django.contrib import admin
from pos.models import *



admin.site.register(CoreUserCategory)
admin.site.register(CoreUser)
admin.site.register(Department)
admin.site.register(StoreTiming)
admin.site.register(Banner)
admin.site.register(Setting)


@admin.register(POSUser)
class POSUserAdmin(admin.ModelAdmin):
    fields = ('vendor', 'username', 'password', 'name', 'phone_number', 'email', 'is_active',)
    
    list_display = ('name', 'phone_number', 'is_active', 'vendor',)
    list_filter = ('is_active', 'vendor',)
    search_fields = ('name', 'phone_number', 'email',)
    ordering = ('vendor', 'name', 'is_active',)
    # show_facets = admin.ShowFacets.ALWAYS
