from modeltranslation.translator import register, TranslationOptions
from .models import *



@register(ProductModifierGroup)
class ProductModifierGroupTranslationOptions(TranslationOptions):
    fields = ('name', 'modifier_group_description',)


@register(ProductModifier)
class ProductModifierTranslationOptions(TranslationOptions):
    fields = ('modifierName', 'modifierDesc',)