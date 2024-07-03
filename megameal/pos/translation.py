from modeltranslation.translator import register, TranslationOptions
from .models import *



@register(POSUser)
class POSUserTranslationOptions(TranslationOptions):
    fields = ('name',)