from django.contrib import admin
from .models import Analysis,Asset
from retirement.models import AssetInstance

admin.site.register(Asset)
admin.site.register(AssetInstance)
admin.site.register(Analysis)