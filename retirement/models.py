from django.db import models
import uuid
from django.urls.base import reverse
from datetime import timedelta
from django.db.models import signals
from django.dispatch.dispatcher import receiver

class Analysis(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Analysis Id")
    title=models.CharField(max_length=100, null=False, help_text =" Short Title For Analysis")
    assets=models.ManyToManyField('Asset',help_text="Add the asset to an Analysis. Remember, results are per analysis")
    create_date=models.DateField(null=False, auto_now_add=True)
    update_date=models.DateField(null=False, auto_now=True)
    
    
    class Meta:
        verbose_name_plural="Analyses"
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        """
        Returns the url to access a particular instance of the model.
        """
        return reverse('analysis-detail', args=[str(self.id)])
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


asset_balances=dict()        
    
@receiver(signals.post_save, sender=Analysis)
def create_transactions(sender, instance,**kwargs):
    print(Asset.objects.filter(analysis__id=instance.id))
    for related_asset in Asset.objects.filter(analysis__id=instance.id):
        instance.title=instance.title + "asset: "+related_asset.name
        print(related_asset.name)
        for asset_instance in AssetInstance.objects.filter(asset__id=related_asset.id):
            tx=Transaction()
            tx.analysis=instance
            tx.txDate=asset_instance.txDate
            tx.oldVal=asset_balances.get(related_asset.id)
            if(tx.oldVal==None):
                asset_balances[related_asset.id]=0
            tx.oldVal=asset_balances[related_asset.id]
            tx.newVal=asset_balances[related_asset.id]+asset_instance.txAmountMin
            tx.description="A "+related_asset.txtype +" of "+ str(asset_instance.txAmountMin) +" for "+related_asset.name + " on "+str(tx.txDate)
            tx.save()
    

class Transaction(models.Model):
    id=models.AutoField(primary_key=True, help_text="Transaction Id")
    txDate=models.DateField(null=False)
    description=models.CharField(max_length=500)
    oldVal=models.FloatField(null=False)
    newVal=models.FloatField(null=False) 
    analysis=models.ForeignKey('Analysis',on_delete=models.CASCADE, help_text="All transactions in the analysis")
    create_date=models.DateField(null=False, auto_now_add=True)
    update_date=models.DateField(null=False, auto_now=True)

    class Meta:
        verbose_name_plural="Transactions"
        
    def __str__(self):
        return self.description
    
    

class AssetInstance(models.Model):
    id=models.AutoField(primary_key=True, help_text="Asset Instance Id")
    asset=models.ForeignKey('Asset',on_delete=models.CASCADE, help_text="Refer to the asset that created it")
    txAmountMin=models.IntegerField(default=0)
    txAmountMax=models.IntegerField(default=0)
    txDate=models.DateField(null=False)
    create_date=models.DateField(null=False, auto_now_add=True)
    update_date=models.DateField(null=False, auto_now=True)
    
    class Meta:
        verbose_name_plural="Asset Instances"
    
    def __str__(self):
        return self.asset.name
    
    def get_absolute_url(self):
        """
        Returns the url to access a particular instance of the model.
        """
        return reverse('asset-inst-detail', args=[str(self.id)])    

class Asset(models.Model):
    
    Currency=(
        ('USD','USD'),
        ('EUR','EUR'),
        ('INR','INR')
    )
    
    TxType=(
        ('CREDIT','CREDIT'),
        ('DEBIT','DEBIT')
    )
    
    Frequency = (
        (1,'DAILY'),
        (7,'WEEKLY'),
        (30,'MONTHLY'),
        (365,'ANNUAL')
    )
    
    Liquidity=(
        (10,'PERM_FIXED_ASSET'),
        (20,'FIXED_ASSET'),
        (30,'DEPOSITS'),
        (40,'SAVINGS'),
        (50,'FLUID')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Unique Asset Identifier")
    #analysis=models.ManyToManyField(Analysis,help_text="Add the analysis to an asset. Remember, results are per analysis")
    name=models.CharField(max_length=100, help_text="Enter the uniquely identifiable name of the asset")
    description=models.TextField(max_length=1000, null=True, help_text=" Asset Description")
    amount  = models.IntegerField(null=False)
    currency=models.CharField(max_length=10, null=False, choices=Currency)
    txtype=models.CharField(max_length=10, null=False, choices=TxType, default='DEBIT')
    acquire_date=models.DateField()
    liquidity=models.IntegerField(null=False,choices=Liquidity, default=50)
    recurrence =models.IntegerField (null=False, default=1)
    frequency=models.IntegerField(null=False, choices=Frequency, default=365)
    conservative_growth_rate=models.FloatField(null=False, default=2.0)
    liberal_growth_rate=models.FloatField(null=False, default=6.0)
    active=models.BooleanField(null=False, default=True)
    create_date=models.DateField(null=False, auto_now_add=True)
    update_date=models.DateField(null=False, auto_now=True)
    
    
    def save(self, *args, **kwargs):
        self.delete_old_asset_instances()
        self.create_asset_instances()
        super().save(*args, **kwargs)
    
    
    def delete_old_asset_instances(self):
        related_asset_instances=AssetInstance.objects.filter(asset__id=self.id)
        for asset_instance in related_asset_instances:
            asset_instance.delete()
    
    def create_asset_instances(self):
        i=0
        while(i<self.recurrence):
            try:
                asset_instance=AssetInstance()
                asset_instance.txAmountMin=self.amount*((1+self.conservative_growth_rate/100)**(i*(365/self.frequency)))
                asset_instance.txAmountMax=self.amount*((1+self.liberal_growth_rate/100)**(i*(365/self.frequency)))
                asset_instance.txDate=self.acquire_date+timedelta(i*self.frequency)#change to add at exact frequency later
                asset_instance.asset=self
                asset_instance.save()
            except:
                #do nothing. just eat it up
                #print("Unexpected error:")
                pass
            i+=1
        

    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        """
        Returns the url to access a particular instance of the model.
        """
        return reverse('asset-detail', args=[str(self.id)])
