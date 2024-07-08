from django.db import models
from core.utils import CorePlatform, TaxLevel, OrderAction
from pos.language import product_tag_locale
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
import string
import secrets



class VendorType(models.Model):
    type = models.CharField(max_length=100)

    def __str__(self):
        return self.type


class Vendor(models.Model):
    Name = models.CharField(max_length=122)
    Email = models.EmailField()
    Password = models.CharField(max_length=122, null=True)
    vendor_type = models.ForeignKey(VendorType, on_delete=models.CASCADE, null=True)
    phone_number = models.PositiveBigIntegerField(null=True)
    gst_number = models.CharField(max_length=20, null=True)
    address_line_1 = models.TextField(null=True)
    address_line_2 = models.TextField(null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=100, null=True)
    country = models.CharField(max_length=100, null=True)
    contact_person_name = models.CharField(max_length=100, null=True)
    contact_person_phone_number = models.PositiveBigIntegerField(null=True)
    currency = models.CharField(max_length=20)
    currency_symbol = models.CharField(max_length=20)
    primary_language = models.CharField(max_length=100, default="English")
    secondary_language = models.CharField(max_length=100, null=True)
    selected_language = models.CharField(max_length=100, default="English") # field used for POS setting for Flutter
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.Name

class Core_User(models.Model):
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=122)
    is_active = models.BooleanField(default=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)


class ProductCategory(models.Model):
    categoryStation = models.ForeignKey("koms.Station", on_delete=models.CASCADE,null=True,blank=True)
    categoryName = models.CharField(max_length=200)
    categoryName_locale = models.CharField(max_length=200, null=True)
    categoryParentId = models.ForeignKey('ProductCategory', on_delete=models.CASCADE, null=True)
    categoryDescription = models.TextField(null=True)
    categoryDescription_locale = models.TextField(null=True)
    categoryPLU = models.CharField(max_length=122)
    categorySlug = models.SlugField(null=True)
    categoryImage = models.ImageField(upload_to='static/images/Category/', height_field=None, width_field=None, max_length=None, null=True)
    categoryImageUrl = models.URLField(null=True)
    image_selection = models.CharField(max_length=20, null=True, choices = (("image", "image"), ("url", "url")))
    categoryIsDeleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, related_name="vendor_category")

    class Meta:
        unique_together = ('categoryPLU', 'vendorId')

    def save(self, *args, **kwargs):
        if not self.categoryPLU:
            unique_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            self.categoryPLU = unique_id

        if not self.categorySlug:
            self.categorySlug = slugify(self.categoryName)

        if not self.categoryName_locale:
            self.categoryName_locale = self.categoryName

        if not self.categoryDescription_locale:
            self.categoryDescription_locale = self.categoryDescription

        super().save(*args, **kwargs)

        return self
    
    def __str__(self):
        return self.categoryName


class Product(models.Model):
    PLU = models.CharField(max_length=50)
    SKU = models.CharField(max_length=50, null=True)
    productName = models.CharField(max_length=200)
    productName_locale = models.CharField(max_length=200, null=True)
    productDesc = models.TextField(default="", null=True)
    productDesc_locale = models.TextField(default="", null=True)
    productParentId = models.ForeignKey("Product", on_delete=models.CASCADE, null=True)
    productThumb = models.ImageField(upload_to='static/images/product/', height_field=None, width_field=None, max_length=None, null=True)
    productPrice = models.FloatField()
    preparationTime = models.IntegerField(default=0)
    productType = models.CharField(max_length=50)## Regular ,Variant
    is_unlimited = models.BooleanField(default=False)
    taxable = models.BooleanField(default=False)
    tag = models.CharField(max_length=50, null=True, choices=(("veg", "veg"), ("non-veg", "non-veg")))
    tag_locale = models.CharField(max_length=50, null=True, choices=product_tag_locale)
    is_displayed_online = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    isDeleted = models.BooleanField(default=False)
    meta = models.JSONField(null=True,blank=True)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('PLU', 'vendorId')

    def save(self, *args, **kwargs):
        if not self.PLU:
            unique_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(15))
            self.PLU = unique_id
            self.SKU = unique_id

        if self.PLU and not self.SKU:
            self.SKU = self.PLU

        if not self.productName_locale:
            self.productName_locale = self.productName

        if not self.productDesc_locale:
            self.productDesc_locale = self.productDesc

        super().save(*args, **kwargs)

        return self

    def __str__(self):
        return self.productName


class ProductImage(models.Model):
    url=models.URLField(max_length=500, null=True, blank=True)
    product=models.ForeignKey(Product, on_delete=models.CASCADE)
    image=models.ImageField(upload_to='static/images/product_images/kiosk', height_field=None, width_field=None, max_length=None, null=True, blank=True)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    is_url_selected = models.BooleanField(default=False)
    is_image_selected = models.BooleanField(default=False)


class ProductCategoryJoint(models.Model):
    product=models.ForeignKey(Product, on_delete=models.CASCADE,null=True,blank=True)
    category=models.ForeignKey(ProductCategory, on_delete=models.CASCADE,null=True,blank=True)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE,null=True,blank=True)

    class Meta:
        unique_together = ('product', 'category', 'vendorId')


class ProductModifierGroup(models.Model):
    name = models.CharField(max_length=200)
    name_locale = models.CharField(max_length=200, null=True)
    modifier_group_description = models.TextField(null=True)
    modifier_group_description_locale = models.TextField(null=True)
    PLU = models.CharField(max_length=50)
    slug = models.CharField(max_length=50,blank=True,null=True)
    min = models.IntegerField()
    max = models.IntegerField()
    active = models.BooleanField(default=True)
    isDeleted = models.BooleanField(default=False)
    modGrptype = models.CharField(max_length=50, default="MULTIPLE")
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('PLU', 'vendorId')

    def save(self, *args, **kwargs):
        if not self.PLU:
            unique_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            self.PLU = unique_id

        if not self.slug:
            self.slug = slugify(self.name)

        if not self.name_locale:
            self.name_locale = self.name

        if not self.modifier_group_description_locale:
            self.modifier_group_description_locale = self.modifier_group_description

        super().save(*args, **kwargs)

        return self
    
    def __str__(self):
        return self.name


class ProductModifier(models.Model):
    modifierName = models.CharField(max_length=122)
    modifierName_locale = models.CharField(max_length=122, null=True)
    modifierDesc = models.CharField( max_length=122, null=True)
    modifierDesc_locale = models.CharField(max_length=122, null=True)
    modifierPLU = models.CharField(max_length=122)
    modifierSKU = models.CharField(max_length=122, null=True)
    modifierImg = models.URLField(max_length=500, null=True)
    modifierPrice = models.FloatField(null=True)
    parentId = models.ForeignKey(ProductModifierGroup, on_delete=models.CASCADE, null=True)
    active = models.BooleanField(default=True)
    isDeleted = models.BooleanField(default=False)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('modifierPLU', 'vendorId')

    def save(self, *args, **kwargs):
        if not self.modifierPLU:
            unique_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            self.modifierPLU = unique_id
            self.modifierSKU = unique_id

        if self.modifierPLU and not self.modifierSKU:
            self.modifierSKU = self.modifierPLU

        if not self.modifierName_locale:
            self.modifierName_locale = self.modifierName

        if not self.modifierDesc_locale:
            self.modifierDesc_locale = self.modifierDesc
        
        super().save(*args, **kwargs)
        return self
    
    def __str__(self):
        return self.modifierName


class ProductAndModifierGroupJoint(models.Model):
    modifierGroup=models.ForeignKey(ProductModifierGroup, on_delete=models.CASCADE,null=True,blank=True)
    product=models.ForeignKey(Product, on_delete=models.CASCADE,null=True,blank=True)
    min=models.IntegerField(default=0)
    max=models.IntegerField(default=0)
    active=models.BooleanField(default=True)
    isEnabled=models.BooleanField(default=False)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True,blank=True)

    class Meta:
        unique_together = ('product', 'modifierGroup')
        
    def __str__(self):
        return self.modifierGroup.name+" | "+self.product.productName


class ProductModifierAndModifierGroupJoint(models.Model):
    modifierGroup = models.ForeignKey(ProductModifierGroup, on_delete=models.CASCADE, related_name='modifier_group_id', null=True, blank=True)
    modifier = models.ForeignKey(ProductModifier, on_delete=models.CASCADE, related_name='modifier_id', null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='vendor_id', null=True, blank=True)

    class Meta:
        unique_together = ('modifier', 'modifierGroup','vendor')

    # def __str__(self):
    #     return self.modifierGroup.name+" | "+self.modifier.modifierName


class Product_Option(models.Model):
    vendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    name=models.CharField(max_length=122)
    optionId=models.CharField(max_length=122)
    isDeleted=models.BooleanField(default=False)


class Product_Option_Value(models.Model):
    vendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    optionsName=models.CharField(max_length=122)
    itemOptionId=models.CharField(max_length=122)
    sortOrder=models.IntegerField(default=0)
    optionId=models.ForeignKey(Product_Option,on_delete=models.CASCADE)
    isDeleted=models.BooleanField(default=False)


class Product_Option_Joint(models.Model):
    vendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    productId=models.ForeignKey(Product,on_delete=models.CASCADE)
    optionId=models.ForeignKey(Product_Option,on_delete=models.CASCADE)
    optionValueId=models.ForeignKey(Product_Option_Value,on_delete=models.CASCADE)


class Product_Tax(models.Model):
    vendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    isDeleted=models.BooleanField(default=False)
    name=models.CharField(max_length=122)
    percentage=models.FloatField()
    enabled=models.BooleanField(default=True)
    posId=models.CharField(max_length=122)
    taxLevel=models.IntegerField(choices=TaxLevel.choices, default=TaxLevel.ORDER,null=True,blank=True)

    def to_dict(self):
        return {
            'vendorId': self.vendorId.pk,
            'isDeleted': self.isDeleted,
            'name': self.name,
            'percentage': self.percentage,
            'enabled': self.enabled,
            'posId': self.posId,
            'taxLevel':self.taxLevel
        }


class Product_Taxt_Joint(models.Model):
    vendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    productId=models.ForeignKey(Product,on_delete=models.CASCADE)
    taxId=models.ForeignKey(Product_Tax,on_delete=models.CASCADE)

    
class Transaction_History(models.Model):
    vendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    transactionData=models.JSONField()
    createdAt=models.DateTimeField(auto_now_add=True,null=True,blank=True)
    transactionType=models.CharField(max_length=122)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        return self


class POS_Settings(models.Model):
    Name=models.CharField(max_length=122)
    VendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    className=models.CharField(max_length=122)
    baseUrl=models.CharField(max_length=255,blank=True)
    secreateKey=models.CharField(max_length=122,blank=True)
    secreatePass=models.CharField(max_length=122,blank=True)
    openOrder=models.CharField(max_length=255,blank=True)
    addItem=models.CharField(max_length=255,blank=True)
    getDiscount=models.CharField(max_length=255,blank=True)
    applyDiscount=models.CharField(max_length=255,blank=True)
    payBill=models.CharField(max_length=255,blank=True)
    meta=models.JSONField(null=True,blank=True)
    store_status = models.BooleanField(default=False)


class Platform(models.Model):
    Name = models.CharField(max_length=20, choices=(
        ('POS', 'POS'), ('WOMS', 'WOMS'), ('KOMS', 'KOMS'), ('Kiosk', 'Kiosk'),
        ('Inventory', 'Inventory'), ('Mobile App', 'Mobile App'), ('Website', 'Website'),
    ))
    Name_ar = models.CharField(max_length=100, choices=(
        ('نقاط البيع', 'POS'), ('وومز', 'WOMS'), ('يأتي', 'KOMS'), ('كشك', 'Kiosk'),
        ('جرد', 'Inventory'), ('تطبيق الجوال', 'Mobile App'), ('موقع إلكتروني', 'Website'),
    ))
    corePlatformType = models.IntegerField(choices=CorePlatform.choices)
    className = models.CharField(max_length=122)
    orderActionType = models.IntegerField(choices=OrderAction.choices, blank=True, null=True)
    baseUrl = models.CharField(max_length=122, blank=True)
    secreateKey = models.CharField(max_length=122, blank=True)
    secreatePass = models.CharField(max_length=122, blank=True)
    APIKey = models.CharField(max_length=122, blank=True)
    macId = models.CharField(max_length=122, blank=True)
    pushMenuUrl = models.URLField(null=True, blank=True)
    autoSyncMenu = models.BooleanField(default=False)
    expiryDate = models.DateTimeField(auto_now=False)
    isActive = models.BooleanField(default=False)
    VendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    
    def to_dict(self):
        return {
            'Name': self.Name,
            'baseUrl': self.baseUrl,
            'secreateKey': self.secreateKey,
            'secreatePass': self.secreatePass,
            'APIKey': self.APIKey,
            'VendorId': self.VendorId,
            'macId':self.macId,
            'isActive':self.isActive,
            'expiryDate':self.expiryDate,
            'pushMenuUrl':self.pushMenuUrl,
            'corePlatformType':self.corePlatformType,
            'className':self.className,
            'autoSyncMenu':self.autoSyncMenu
        }
    
    def __str__(self):
        return self.Name
       
       
class Api_Logs(models.Model):
    reason=models.CharField(max_length=122,null=True,blank=True)
    status=models.IntegerField(null=True,blank=True)
    response=models.JSONField(null=True,blank=True)


class Vendor_Settings(models.Model):
    VendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    orderPrepTime=models.IntegerField(null=True,blank=True)
    currencyCode=models.CharField(max_length=20)


class Token_date(models.Model):
    Date=models.DateTimeField()
    Token=models.IntegerField(max_length=200,)     


class json_data(models.Model):
    json_data=models.TextField()
 

class woocommerce_key_table(models.Model):
    url=models.URLField(blank=True ,)
    consumer_key=models.CharField(max_length=250,unique=True,null=True)
    consumer_secret=models.CharField(max_length=200) 
    version=models.CharField(max_length=200)


from order.models import Customer, Order # Placed here due to circular import
class EmailLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_email")
    sender = models.CharField(max_length=100)
    receiver = models.CharField(max_length=100)
    subject = models.CharField(max_length=500)
    email_body_type = models.CharField(max_length=10)
    email_body = models.TextField(max_length=10000)
    status = models.CharField(max_length=2000)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="customer_email")
    created_at = models.DateTimeField(auto_now_add=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_email_log")



@receiver(post_save, sender=Vendor)
def deactivate_related_platforms(sender, instance, **kwargs):
    if not kwargs.get('raw', False):  # To avoid signal firing during bulk operations
        if instance.is_active is False:  # When is_active of Vendor changes to False
            related_platforms = Platform.objects.filter(VendorId=instance)
            related_platforms.update(isActive=False)
