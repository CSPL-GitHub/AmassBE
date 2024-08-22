from django.db import models
from core.utils import TaxLevel, OrderAction
from pos.model_choices import platform_choices
from pos.language import platform_locale
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
    vendor_type = models.ForeignKey(VendorType, on_delete=models.CASCADE)
    phone_number = models.PositiveBigIntegerField()
    gst_number = models.CharField(max_length=20, null=True, blank=True)
    address_line_1 = models.TextField()
    address_line_2 = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    contact_person_name = models.CharField(max_length=100)
    contact_person_phone_number = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=20)
    currency_symbol = models.CharField(max_length=20)
    primary_language = models.CharField(max_length=100, default="English")
    secondary_language = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_franchise_owner = models.BooleanField(default=False)
    franchise = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    logo = models.ImageField(upload_to='vendor_logo', null=True, blank=True)


    def __str__(self):
        return f"{self.Name}({self.pk})"


class VendorSocialMedia(models.Model):
    name = models.CharField(max_length=20, choices=(
        ('twitter', 'twitter'), ('instagram', 'instagram'), ('pinterest', 'pinterest'), 
        ('linkedIn', 'linkedIn'),('facebook','facebook')
    ))
    link = models.URLField(max_length=500,null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class ProductCategory(models.Model):
    categoryStation = models.ForeignKey("koms.Station", on_delete=models.CASCADE)
    categoryName = models.CharField(max_length=200)
    categoryName_locale = models.CharField(max_length=200, null=True, blank=True)
    categoryParentId = models.ForeignKey('ProductCategory', on_delete=models.CASCADE, null=True, blank=True)
    categoryDescription = models.TextField(null=True, blank=True)
    categoryDescription_locale = models.TextField(null=True, blank=True)
    categoryPLU = models.CharField(max_length=122)
    categorySlug = models.SlugField(null=True, blank=True)
    categoryImage = models.ImageField(upload_to='static/images/Category/', height_field=None, width_field=None, max_length=None, null=True, blank=True)
    categoryImageUrl = models.URLField(max_length=500, null=True, blank=True)
    image_selection = models.CharField(max_length=20, null=True, blank=True, choices = (("image", "image"), ("url", "url")))
    categoryIsDeleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_category")

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
            if self.categoryDescription:
                self.categoryDescription_locale = self.categoryDescription

        super().save(*args, **kwargs)

        return self
    
    def __str__(self):
        return self.categoryName


class Product(models.Model):
    PLU = models.CharField(max_length=50)
    SKU = models.CharField(max_length=50, null=True, blank=True)
    productName = models.CharField(max_length=200)
    productName_locale = models.CharField(max_length=200, null=True, blank=True)
    productDesc = models.TextField(default="", null=True, blank=True)
    productDesc_locale = models.TextField(default="", null=True, blank=True)
    productParentId = models.ForeignKey("Product", on_delete=models.CASCADE, null=True, blank=True)
    productThumb = models.ImageField(upload_to='static/images/product/', height_field=None, width_field=None, max_length=None, null=True, blank=True)
    productPrice = models.FloatField()
    preparationTime = models.IntegerField(default=0)
    recipe_video_url = models.URLField(max_length=1000, null=True, blank=True)
    productType = models.CharField(max_length=50)## Regular ,Variant
    is_unlimited = models.BooleanField(default=False)
    taxable = models.BooleanField(default=False)
    tag = models.CharField(max_length=50, null=True, blank=True, choices=(("veg", "veg"), ("non-veg", "non-veg")))
    is_displayed_online = models.BooleanField(default=True)
    is_todays_special = models.BooleanField(default=False)
    is_in_recommendations = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    isDeleted = models.BooleanField(default=False)
    meta = models.JSONField(null=True, blank=True)
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
            if self.productDesc:
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
    product=models.ForeignKey(Product, on_delete=models.CASCADE)
    category=models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'category', 'vendorId')


class ProductModifierGroup(models.Model):
    name = models.CharField(max_length=200)
    name_locale = models.CharField(max_length=200, null=True, blank=True)
    modifier_group_description = models.TextField(null=True, blank=True)
    modifier_group_description_locale = models.TextField(null=True, blank=True)
    PLU = models.CharField(max_length=50)
    slug = models.CharField(max_length=50, null=True, blank=True)
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
            if self.modifier_group_description:
                self.modifier_group_description_locale = self.modifier_group_description

        super().save(*args, **kwargs)

        return self
    
    def __str__(self):
        return self.name


class ProductModifier(models.Model):
    modifierName = models.CharField(max_length=122)
    modifierName_locale = models.CharField(max_length=122, null=True, blank=True)
    modifierDesc = models.CharField( max_length=122, null=True, blank=True)
    modifierDesc_locale = models.CharField(max_length=122, null=True, blank=True)
    modifierPLU = models.CharField(max_length=122)
    modifierSKU = models.CharField(max_length=122, null=True, blank=True)
    modifierImg = models.URLField(max_length=500, null=True, blank=True)
    modifierPrice = models.FloatField(null=True, blank=True)
    parentId = models.ForeignKey(ProductModifierGroup, on_delete=models.CASCADE, null=True, blank=True)
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
            if self.modifierDesc:
                self.modifierDesc_locale = self.modifierDesc
        
        super().save(*args, **kwargs)
        return self
    
    def __str__(self):
        return self.modifierName


class ProductAndModifierGroupJoint(models.Model):
    modifierGroup=models.ForeignKey(ProductModifierGroup, on_delete=models.CASCADE)
    product=models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    min=models.IntegerField(default=0)
    max=models.IntegerField(default=0)
    active=models.BooleanField(default=True)
    isEnabled=models.BooleanField(default=False)
    vendorId=models.ForeignKey(Vendor, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'modifierGroup')
        
    def __str__(self):
        return self.modifierGroup.name+" | "+self.product.productName


class ProductModifierAndModifierGroupJoint(models.Model):
    modifierGroup = models.ForeignKey(ProductModifierGroup, on_delete=models.CASCADE, related_name='modifier_group_id')
    modifier = models.ForeignKey(ProductModifier, on_delete=models.CASCADE, related_name='modifier_id')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='vendor_id')

    class Meta:
        unique_together = ('modifier', 'modifierGroup','vendor')


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


class Tax(models.Model):
    name = models.CharField(max_length=122)
    name_locale = models.CharField(max_length=122, null=True, blank=True)
    percentage = models.FloatField()
    taxLevel = models.IntegerField(choices=TaxLevel.choices, default=TaxLevel.ORDER, null=True, blank=True)
    enabled = models.BooleanField(default=True)
    isDeleted = models.BooleanField(default=False)
    vendorId = models.ForeignKey(Vendor,on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.name_locale:
            self.name_locale = self.name

        super().save(*args, **kwargs)
        
        return self

    def __str__(self):
        return self.name
    
    def to_dict(self):
        return {
            'vendorId': self.vendorId.pk,
            'isDeleted': self.isDeleted,
            'name': self.name,
            'percentage': self.percentage,
            'enabled': self.enabled,
            'taxLevel':self.taxLevel
        }


class Product_Taxt_Joint(models.Model):
    vendorId=models.ForeignKey(Vendor,on_delete=models.CASCADE)
    productId=models.ForeignKey(Product,on_delete=models.CASCADE)
    taxId=models.ForeignKey(Tax,on_delete=models.CASCADE)


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
    Name = models.CharField(max_length=20, choices=platform_choices)
    Name_locale = models.CharField(max_length=100, choices=platform_locale)
    orderActionType = models.IntegerField(choices=OrderAction.choices, null=True, blank=True)
    baseUrl = models.CharField(max_length=122, blank=True)
    secreateKey = models.CharField(max_length=122, blank=True)
    secreatePass = models.CharField(max_length=122, blank=True)
    expiryDate = models.DateTimeField(auto_now=False)
    isActive = models.BooleanField(default=False)
    VendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    
    def to_dict(self):
        return {
            'Name': self.Name,
            'baseUrl': self.baseUrl,
            'secreateKey': self.secreateKey,
            'secreatePass': self.secreatePass,
            'VendorId': self.VendorId,
            'isActive':self.isActive,
            'expiryDate':self.expiryDate,
        }
    
    def __str__(self):
        return self.Name 


from order.models import Customer, Order # Placed here due to circular import error
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
