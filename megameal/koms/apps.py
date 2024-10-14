from django.apps import AppConfig


class KomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'koms'

    def ready(self):
        import koms.signals
