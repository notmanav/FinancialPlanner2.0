import uuid
import logging
from django.db import models
from django.urls.base import reverse
from retirement.utils import DateUtil, MoneyUtil
from retirement.utils import MoneyUtil
from django.db.models import Q
from _collections import defaultdict


logger = logging.getLogger('django')
moneyutil=MoneyUtil()
TARGET_CURRENCY='USD'

class Result(models.Model):
    id=models.AutoField(primary_key=True, help_text="Result Id(Servers no purpose other then letting the Analysis transaction complete before doing the calculations")
    analysis=models.OneToOneField('Analysis',on_delete=models.CASCADE)

    interest_dates_cache=defaultdict(list)
    moneyutil=MoneyUtil()

    def save(self, *args, **kwargs):
        self.delete_old_transactions()
        super().save(*args, **kwargs)
        self.create_transactions()

    def __str__(self):
        return (self.analysis.title + "-Results")


    def is_interest_day(self,related_asset,txDate):
        dates=self.interest_dates_cache.get(related_asset.id)
        if(dates==None or len(dates)==0):
            dates=list()
            dates.extend(related_asset.calc_next_x_interest_days(related_asset.acquire_date,10))
            self.interest_dates_cache[related_asset.id]=dates
        elif(dates[-1] < txDate):
            dates.extend(related_asset.calc_next_x_interest_days(dates[-1],len(dates)))
        if txDate in dates:
            return True
        else:
            return False


    def create_transactions(self):
        dateutility=DateUtil()
        #print(Asset.objects.filter(analysis__id=self.analysis.id))
        related_assets=Asset.objects.filter(analysis__id=self.analysis.id)
        for related_asset in related_assets:
            related_asset.prep_for_txn()
            related_asset.save()

        current_tx_date=self.analysis.start_date

        asset_instances_of_id=dict()
        related_assets=Asset.objects.filter(analysis__id=self.analysis.id)
        for related_asset in related_assets:
            asset_instances_of_id[related_asset.id]=AssetInstance.objects.filter(asset__id=related_asset.id)
        while(current_tx_date<=self.analysis.end_date):
            #related_assets=Asset.objects.filter(analysis__id=self.analysis.id)
            for related_asset in related_assets:
                if(self.is_interest_day(related_asset,current_tx_date) and related_asset.txtype=='CREDIT'):
                    new_conservative_amount=related_asset.get_next_conservative_interest_amount()
                    new_liberal_amount=related_asset.get_next_liberal_interest_amount()
                    if(new_conservative_amount>0):
                        tx=Transaction()
                        tx.analysis=self.analysis
                        tx.txDate=current_tx_date
                        tx.oldVal=related_asset.conservative_balance
                        tx.newVal=new_conservative_amount
                        tx.txtype=related_asset.txtype
                        tx.txcause='interest'
                        tx.causing_asset_id=related_asset.id
                        tx.impacted_asset_id=related_asset.id
                        related_asset.conservative_balance=new_conservative_amount
                        tx.description="An interest "+related_asset.txtype +" of "+ str(round(tx.newVal-tx.oldVal,2)) +" for "+related_asset.name + " on "+str(tx.txDate)+" for a total new balance of "+str(round(tx.newVal,2))
                        tx.save()
                        related_asset.save()
                    if(new_liberal_amount>0):
                        tx=Transaction()
                        tx.analysis=self.analysis
                        tx.txDate=current_tx_date
                        tx.oldVal=related_asset.libe_balance
                        tx.newVal=new_liberal_amount
                        tx.txtype=related_asset.txtype
                        tx.txcause='interest'
                        tx.causing_asset_id=related_asset.id
                        tx.impacted_asset_id=related_asset.id
                        related_asset.conservative_balance=new_liberal_amount
                        tx.description="An interest(liberal) "+related_asset.txtype +" of "+ str(round(tx.newVal-tx.oldVal,2)) +" for "+related_asset.name + " on "+str(tx.txDate)+" for a total new balance of "+str(round(tx.newVal,2))
                        tx.save()
                        related_asset.save()
                for asset_instance in asset_instances_of_id.get(related_asset.id):
                    if(asset_instance.txDate==current_tx_date):
                        if(related_asset.txtype=='CREDIT'):
                            tx=Transaction()
                            tx.analysis=self.analysis
                            tx.txDate=asset_instance.txDate
                            tx.oldVal=related_asset.conservative_balance
                            tx.newVal=tx.oldVal+asset_instance.txAmountMin
                            tx.txtype='CREDIT'
                            tx.txcause='recurring asset'
                            tx.causing_asset_id=related_asset.id
                            tx.impacted_asset_id=related_asset.id
                            related_asset.conservative_balance=tx.newVal
                            tx.description="A "+related_asset.txtype +" of "+ str(round(asset_instance.txAmountMin,2)) +" for "+related_asset.name + " on "+str(tx.txDate) +" for a total new balance of "+str(tx.newVal)
                            tx.save()
                            related_asset.save()
                        else:
                            # A super conservative approach will be to reduce liberal expenses from conservative assets but let's stick to conservative or liberal for both to have a realistic dataset
                            self.reduce_next_most_liquid_asset_value(asset_instance.txAmountMax,related_asset.currency ,asset_instance.txDate,related_asset.name,related_asset.id)
            current_tx_date=dateutility.add_days(current_tx_date, 1)

    def reduce_next_most_liquid_asset_value(self,value, currency, txDate, asset_name, asset_id):
        #get the next most liquid asset and create a new debit transaction on that asset;recursively
        next_most_liquid_asset=Asset.objects.filter(~Q(conservative_balance=0.0)).order_by('-liquidity','-conservative_balance')[0]
        if(next_most_liquid_asset==None):
            logger.debug('No more money left. Crapping out... on '+str(txDate))
            return
        value_in_new_currency=moneyutil.convertAmount(value, currency, next_most_liquid_asset.currency)
        if(next_most_liquid_asset.conservative_balance>value_in_new_currency):
            tx=Transaction()
            tx.analysis=self.analysis
            tx.txDate=txDate
            tx.oldVal=next_most_liquid_asset.conservative_balance
            next_most_liquid_asset.conservative_balance-=value_in_new_currency
            tx.newVal=next_most_liquid_asset.conservative_balance
            tx.txtype='DEBIT'
            tx.txcause='adjustment against an expense'
            tx.causing_asset_id=asset_id
            tx.impacted_asset_id=next_most_liquid_asset.id
            tx.description="A Debit of "+ str(round(value_in_new_currency,2)) +" from "+next_most_liquid_asset.name + " due to "+ asset_name+" on "+str(txDate) +" for a total new balance of "+str(tx.newVal)
            tx.save()
            next_most_liquid_asset.save()
        else:
            next_most_liquid_asset_in_new_currency=moneyutil.convertAmount(next_most_liquid_asset.conservative_balance,next_most_liquid_asset.currency,currency)
            tx=Transaction()
            tx.analysis=self.analysis
            tx.txDate=txDate
            tx.oldVal=next_most_liquid_asset.conservative_balance
            next_most_liquid_asset.conservative_balance=0.0
            tx.newVal=0.0
            tx.txtype='DEBIT'
            tx.txcause='adjustment against an expense'
            tx.causing_asset_id=asset_id
            tx.impacted_asset_id=next_most_liquid_asset.id
            tx.description="A Debit of "+ str(round(tx.oldVal,2)) +" from "+next_most_liquid_asset.name + " due to  "+ asset_name +" on "+str(txDate) +" for a total new balance of "+str(tx.newVal)
            tx.save()
            next_most_liquid_asset.save()
            self.reduce_next_most_liquid_asset_value(value-next_most_liquid_asset_in_new_currency,txDate,asset_name)



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

    id = models.AutoField(primary_key=True, help_text="Unique Asset Identifier")
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


    conservative_balance=models.FloatField(null=False, default=0.0)
    liberal_balance=models.FloatField(null=False, default=0.0)

    active=models.BooleanField(null=False, default=True)
    create_date=models.DateField(null=False, auto_now_add=True)
    update_date=models.DateField(null=False, auto_now=True)

    dateutil=DateUtil()


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
        self.conservative_balance=0.0
        self.liberal_balance=0.0


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

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        Returns the url to access a particular instance of the model.
        """
        return reverse('asset-detail', args=[str(self.id)])

    def calc_next_x_interest_days(self, current_interest_date=acquire_date,x=10):
        dates=list()
        for i in range(x):
            next_date=self.get_next_interest_date(current_interest_date)
            dates.append(next_date)
            current_interest_date=next_date
            i+=1
        return dates


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

class Transaction(models.Model):
    id=models.AutoField(primary_key=True, help_text="Transaction Id")
    txDate=models.DateField(null=False)
    description=models.CharField(max_length=500)
    oldVal=models.FloatField(null=False)
    newVal=models.FloatField(null=False)
    analysis=models.ForeignKey('Analysis',on_delete=models.CASCADE, help_text="All transactions in the analysis")
    txtype=models.CharField(max_length=10, null=False, choices=Asset.TxType, default='DEBIT')
    txcause=models.CharField(max_length=10, null=False, default='INTEREST')
    causing_asset_id=models.IntegerField(default=0, help_text="Enter the uniquely identifiable name of the asset due to which money is being transacted")
    impacted_asset_id=models.IntegerField(default=0,  help_text="Enter the uniquely identifiable name of the asset to which money is being transacted")
    create_date=models.DateField(null=False, auto_now_add=True)
    update_date=models.DateField(null=False, auto_now=True)

    class Meta:
        verbose_name_plural="Transactions"

    def __str__(self):
        return self.description +" || "+str(round(self.oldVal,2))+ " || "+str(round(self.newVal,2))
