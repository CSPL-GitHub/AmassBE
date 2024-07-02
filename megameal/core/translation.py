from modeltranslation.translator import register, TranslationOptions
from .models import *



@register(VendorType)
class VendorTypeTranslationOptions(TranslationOptions):
    fields = ('type',)


@register(Vendor)
class VendorTranslationOptions(TranslationOptions):
    fields = (
        'Name', 'phone_number', 'Password', 
        'address_line_1', 'address_line_2', 'city', 'state', 'country',
        'gst_number', 'contact_person_name', 'contact_person_phone_number',
    )

@register(ProductCategory)
class ProductCategoryTranslationOptions(TranslationOptions):
    fields = ('categoryName', 'categoryDescription',)


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ('productName', 'productDesc', 'productPrice', 'tag',)
