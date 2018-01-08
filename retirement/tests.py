

# Create your tests here.
import unittest
from datetime import date
from retirement.utils import DateUtil

class TestUM(unittest.TestCase):
    
    dateutiltest=None
    def setUp(self):
        self.dateutiltest=DateUtil()

    def test_add_days(self):
        acquire_date=date(2016,2,28)
        self.assertEqual(self.dateutiltest.add_days(acquire_date, 1), date(2016,2,29))

    def test_add_days2(self):
        acquire_date=date(2016,2,28)
        self.assertEqual(self.dateutiltest.add_days(acquire_date, 0), date(2016,2,28))


    def test_add_days3(self):
        acquire_date=date(2016,12,31)
        self.assertEqual(self.dateutiltest.add_days(acquire_date, 1), date(2017,1,1))

    def test_add_months(self):
        acquire_date=date(2016,1,31)
        self.assertEqual(self.dateutiltest.add_months(acquire_date.day,acquire_date, 1), date(2016,2,29))
    
    def test_add_months2(self):
        acquire_date=date(2016,2,29)
        self.assertEqual(self.dateutiltest.add_months(31,acquire_date, 1), date(2016,3,31))

    def test_add_months3(self):
        acquire_date=date(2016,3,28)
        self.assertEqual(self.dateutiltest.add_months(31,acquire_date, 1), date(2016,4,30))

    def test_add_months4(self):
        acquire_date=date(2016,2,29)
        self.assertEqual(self.dateutiltest.add_months(acquire_date.day,acquire_date, 1), date(2016,3,29))

    def test_add_months5(self):
        acquire_date=date(2016,2,29)
        self.assertEqual(self.dateutiltest.add_months(acquire_date.day,acquire_date, 0), date(2016,2,29))
        
    def test_add_years(self):
        acquire_date=date(2016,2,29)
        self.assertEqual(self.dateutiltest.add_years(acquire_date.day, acquire_date, 1),date(2017,2,28))

    def test_add_years2(self):
        acquire_date=date(2015,2,28)
        self.assertEqual(self.dateutiltest.add_years(acquire_date.day, acquire_date, 1),date(2016,2,28))
        
    def test_add_years3(self):
        acquire_date=date(2015,2,28)
        self.assertEqual(self.dateutiltest.add_years(acquire_date.day, acquire_date, 0),date(2015,2,28))


if __name__ == '__main__':
    unittest.main()