from django.apps import AppConfig


class WomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'woms'

    def ready(self):
        import woms.signals
