from modeltranslation.translator import register, TranslationOptions
from woms.models import Waiter, Floor



@register(Waiter)
class WaiterTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Floor)
class FloorTranslationOptions(TranslationOptions):
    fields = ('name',)
