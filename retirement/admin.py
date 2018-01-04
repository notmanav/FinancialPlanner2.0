from django.contrib import admin
from .models import Analysis,Asset
from retirement.models import AssetInstance, Transaction

admin.site.register(Asset)
admin.site.register(AssetInstance)
admin.site.register(Analysis)
admin.site.register(Transaction)
#admin.site.register(Result)