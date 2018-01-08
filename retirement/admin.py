from django.contrib import admin
from retirement.models import Analysis,Asset,AssetInstance, Transaction, Result

admin.site.register(Asset)
admin.site.register(AssetInstance)
admin.site.register(Analysis)
admin.site.register(Transaction)
admin.site.register(Result)