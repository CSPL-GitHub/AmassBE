from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin import widgets
from .models import *


class ManyToManyAdmin(admin.ModelAdmin):
    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        kwargs['widget']= widgets.FilteredSelectMultiple(db_field.verbose_name,db_field.name in self.filter_vertical)
        return super(admin.ModelAdmin, self).formfield_for_manytomany(db_field, request=request, **kwargs)

class ModelAdmin(ManyToManyAdmin):
    pass

admin.site.register(VendorLog,ModelAdmin)
admin.site.register(Modules)
admin.site.register(Permissions,ModelAdmin)
admin.site.register(PermissionGroup,ModelAdmin)