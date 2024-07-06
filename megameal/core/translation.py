from modeltranslation.translator import register, TranslationOptions
from .models import *



@register(VendorType)
class VendorTypeTranslationOptions(TranslationOptions):
    fields = ('type',)


@register(Vendor)
class VendorTranslationOptions(TranslationOptions):
    fields = ('Name', 'contact_person_name',)


@register(ProductCategory)
class ProductCategoryTranslationOptions(TranslationOptions):
    fields = ('categoryName', 'categoryDescription',)


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ('productName', 'productDesc',)


@register(ProductModifierGroup)
class ProductModifierGroupTranslationOptions(TranslationOptions):
    fields = ('name', 'modifier_group_description',)


@register(ProductModifier)
class ProductModifierTranslationOptions(TranslationOptions):
    fields = ('modifierName', 'modifierDesc',)