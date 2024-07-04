from modeltranslation.translator import register, TranslationOptions
from .models import *



@register(Station)
class StationTranslationOptions(TranslationOptions):
    fields = ('station_name',)