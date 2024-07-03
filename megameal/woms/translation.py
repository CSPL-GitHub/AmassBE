from modeltranslation.translator import register, TranslationOptions
from woms.models import Waiter



@register(Waiter)
class WaiterTranslationOptions(TranslationOptions):
    fields = ('name',)
