from modeltranslation.translator import register, TranslationOptions
from .models import *



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