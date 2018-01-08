from datetime import timedelta, date
import calendar

class DateUtil:

    def add_days(self,inthedate,thedays):
        return inthedate+timedelta(days=thedays)

    def add_months(self,txDay,inthedate,months):
        month = inthedate.month - 1 + months
        year = int(inthedate.year + month / 12 )
        month = month % 12 + 1
        day = min(txDay,calendar.monthrange(year,month)[1]) # using txDay to keep the original acquire date for different months
        return date(year,month,day)
    
    def add_years(self, txDay,inthedate,years):
        month = inthedate.month
        year = int(inthedate.year +  years )
        day = min(txDay,calendar.monthrange(year,month)[1]) # using txDay to keep the original acquire date for different months
        return date(year,month,day)
    