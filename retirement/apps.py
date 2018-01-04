from django.apps import AppConfig


class RetirementConfig(AppConfig):
    name = 'retirement'
    
    def ready(self):
        import retirement.signals

