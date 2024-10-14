from django.db import models



class Modules(models.Model):
    module_name=models.CharField(max_length=50)
    def __str__(self):
        return self.module_name

class PermissionGroup(models.Model):
    group_name=models.CharField(max_length=50)
    group_modules=models.ManyToManyField(Modules,null=True,blank=True)
    def __str__(self):
        return self.group_name

class VendorLog(models.Model):
    userName = models.CharField(max_length=122)
    email = models.CharField(max_length=122)        
    password = models.CharField(max_length=12)
    groups=models.ManyToManyField(PermissionGroup,null=True,blank=True)
    module=models.ManyToManyField(Modules,null=True,blank=True)
    def __str__(self):
        return self.userName

class Permissions(models.Model):
    user = models.ForeignKey(VendorLog, on_delete=models.CASCADE,unique=True)
    module=models.ManyToManyField(Modules,null=True,blank=True)
    def __str__(self):
        return ("user :"+str(self.user))