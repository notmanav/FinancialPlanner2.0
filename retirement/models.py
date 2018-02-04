import uuid
from django.db import models
from django.urls.base import reverse
from retirement.utils import DateUtil

class Result(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Result Id(Servers no purpose other then letting the Analysis transaction complete before doing the calculations")
    analysis=models.OneToOneField('Analysis',on_delete=models.CASCADE)
    
    def save(self, *args, **kwargs):
        self.delete_old_transactions()
        super().save(*args, **kwargs)
        self.create_transactions()
        
    def __str__(self):
        return (self.analysis.title + "-Results")
    
    def create_transactions(self):
        dateutility=DateUtil()
        #print(Asset.objects.filter(analysis__id=self.analysis.id))
        related_assets=Asset.objects.filter(analysis__id=self.analysis.id)
        current_tx_date=self.analysis.start_date
        while(current_tx_date<=self.analysis.end_date):
            for related_asset in related_assets:
                related_asset.prep_for_txn()
                if(related_asset.is_interest_day(current_tx_date)):
                    new_conservative_amount=related_asset.get_next_conservative_interest_amount()
                    tx=Transaction()
                    tx.analysis=self.analysis
                    tx.txDate=current_tx_date
                    tx.oldVal=related_asset.conservative_balance
                    tx.newVal=new_conservative_amount
                    related_asset.conservative_balance=new_conservative_amount
                    tx.description="An interest "+related_asset.txtype +" of "+ str(tx.newVal-tx.oldVal) +" for "+related_asset.name + " on "+str(tx.txDate)+" for a total new balance of "+str(tx.newVal)
                    tx.save()
                for asset_instance in AssetInstance.objects.filter(asset__id=related_asset.id):
                    if(asset_instance.txDate==current_tx_date):
                        tx=Transaction()
                        tx.analysis=self.analysis
                        tx.txDate=asset_instance.txDate
                        tx.oldVal=related_asset.conservative_balance
                        tx.newVal=tx.oldVal+asset_instance.txAmountMin
                        related_asset.conservative_balance=tx.newVal
                        tx.description="A "+related_asset.txtype +" of "+ str(asset_instance.txAmountMin) +" for "+related_asset.name + " on "+str(tx.txDate) +" for a total new balance of "+str(tx.newVal)
                        tx.save()
            current_tx_date=dateutility.add_days(current_tx_date, 1)
    
    def delete_old_transactions(self):
        transactions=Transaction.objects.filter(analysis__id=self.analysis.id)
        for transaction in transactions:
            transaction.delete()

class Analysis(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Analysis Id")
    title=models.CharField(max_length=100, null=False, help_text =" Short Title For Analysis")
    assets=models.ManyToManyField('Asset',help_text="Add the asset to an Analysis. Remember, results are per analysis")
    start_date=models.DateField(help_text="Analysis starts from this date. All previous assets transactions will be ignored")
    end_date=models.DateField(help_text="Analysis ends on this date. All future asset transactions will be ignored")
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
        return self.description +" || "+str(self.oldVal)+ " || "+str(self.newVal)
    
    

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
        ordering = ['txDate']
    
    def __str__(self):
        return self.asset.name + " ("+ str(self.txDate) +") - "+str(self.asset.currency)+" "+str(self.txAmountMin) +"/"+str(self.txAmountMax)
    
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
    
    DAILY_FREQ=1
    WEEKLY_FREQ=7
    MONTHLY_FREQ=30
    ANNUAL_FREQ=365
    Frequency = (
        (DAILY_FREQ,'DAILY'),
        (WEEKLY_FREQ,'WEEKLY'),
        (MONTHLY_FREQ,'MONTHLY'),
        (ANNUAL_FREQ,'ANNUAL')
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
    
    asset_recurrence = models.IntegerField (null=False, default=1)
    asset_recurrence_frequency=models.IntegerField(null=False, choices=Frequency, default=ANNUAL_FREQ)
    asset_recurrence_conservative_growth_rate=models.FloatField(null=False, default=2.0)
    asset_recurrence_liberal_growth_rate=models.FloatField(null=False, default=6.0)
    
    interest_recurrence_frequency=models.IntegerField(null=False, choices=Frequency, default=ANNUAL_FREQ)
    interest_recurrence_conservative_growth_rate=models.FloatField(null=False, default=2.0)
    interest_recurrence_liberal_growth_rate=models.FloatField(null=False, default=6.0)
    
    active=models.BooleanField(null=False, default=True)
    create_date=models.DateField(null=False, auto_now_add=True)
    update_date=models.DateField(null=False, auto_now=True)
    
    next_interest_day=None
    dateutil=DateUtil()
    conservative_balance=0.0
    liberal_balance=0.0
    
    
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
        while(i<self.asset_recurrence):
            try:
                asset_instance=AssetInstance()
                asset_instance.txAmountMin=self.amount*((1+self.asset_recurrence_conservative_growth_rate/100)**i)
                asset_instance.txAmountMax=self.amount*((1+self.asset_recurrence_liberal_growth_rate/100)**i)
                asset_instance.txDate=self.get_next_asset_instance_date(i)
                asset_instance.asset=self
                asset_instance.save()
            except Exception as ex:
                #do nothing. just eat it up
                print(ex)
                #pass
            i+=1

    def prep_for_txn(self):
        self.dateutil=DateUtil()
        # self.conservative_balance=0.0
        # self.liberal_balance=0.0
        self.next_interest_day=self.get_next_interest_date(self.acquire_date)
    
    
    def get_next_asset_instance_date(self,recurrence_number):
        if(self.asset_recurrence_frequency==Asset.DAILY_FREQ):
            return self.dateutil.add_days(self.acquire_date, recurrence_number)
        elif(self.asset_recurrence_frequency==Asset.WEEKLY_FREQ):
            return self.dateutil.add_days(self.acquire_date, 1*7*recurrence_number)
        elif(self.asset_recurrence_frequency==Asset.MONTHLY_FREQ):
            return self.dateutil.add_months(self.acquire_date.day,self.acquire_date, recurrence_number)
        elif(self.asset_recurrence_frequency==Asset.ANNUAL_FREQ):
            return self.dateutil.add_years(self.acquire_date.day,self.acquire_date, recurrence_number)
        return self.dateutil.add_years(self.acquire_date.day,self.acquire_date, recurrence_number) #assume annual as the de-facto


    def get_next_conservative_interest_amount(self):
        return self.conservative_balance*(1+(self.interest_recurrence_conservative_growth_rate/100))
    
    def get_next_liberal_interest_amount(self):
        return self.liberal_balance*(1+(self.interest_recurrence_liberal_growth_rate/100))
    
    #Does not change the interest dates. Just returns the next interest date assuming the current_interest_date is valid    
    def get_next_interest_date(self,current_interest_date):
        if(self.interest_recurrence_frequency==Asset.DAILY_FREQ):
            return self.dateutil.add_days(current_interest_date, 1)
        elif(self.interest_recurrence_frequency==Asset.WEEKLY_FREQ):
            return self.dateutil.add_days(current_interest_date, 1*7)
        elif(self.interest_recurrence_frequency==Asset.MONTHLY_FREQ):
            return self.dateutil.add_months(self.acquire_date.day,current_interest_date),1
        elif(self.interest_recurrence_frequency==Asset.ANNUAL_FREQ):
            return self.dateutil.add_years(self.acquire_date.day,current_interest_date,1)
        return self.dateutil.add_years(self.acquire_date.day,current_interest_date,1) #assume annual as the de-facto
    
    #Stateless. Does not set the next interest date by default. Call set_next_interest_day to change tp the next interest day
    def is_interest_day(self,thedate):
        if(thedate==self.next_interest_day):
            return True
        return False
    
    #Stateful. Every call increments the date to next occurrence
    def set_next_interest_day(self):
        self.next_interest_day=self.get_next_interest_date(self.next_interest_day)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        """
        Returns the url to access a particular instance of the model.
        """
        return reverse('asset-detail', args=[str(self.id)])
