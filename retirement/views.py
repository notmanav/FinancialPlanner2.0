from django.shortcuts import render
from retirement.models import Analysis, Asset

def index(request):
    """
    View function for home page of site.
    """
    # Generate counts of some of the main objects
    num_analysis=Analysis.objects.all().count()
    num_assets=Asset.objects.all().count()
    # Available books (status = 'a')
    num_asset_active=Asset.objects.filter(active__exact=True).count()
    
    # Render the HTML template index.html with the data in the context variable
    return render(
        request,
        'index.html',
        context={'num_analysis':num_analysis,'num_assets':num_assets,'num_asset_active':num_asset_active},
    )