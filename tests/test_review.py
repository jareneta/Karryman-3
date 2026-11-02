import unittest
from datetime import datetime,timezone,timedelta
from review import fresh_session,valid_price

class ReviewSafetyTests(unittest.TestCase):
    def test_recent_session(self):
        today=datetime.now(timezone.utc).date()
        self.assertTrue(fresh_session(today.isoformat()))
        self.assertTrue(fresh_session((today-timedelta(days=4)).isoformat()))
    def test_old_future_or_missing_session(self):
        today=datetime.now(timezone.utc).date()
        self.assertFalse(fresh_session((today-timedelta(days=8)).isoformat()))
        self.assertFalse(fresh_session((today+timedelta(days=1)).isoformat()))
        self.assertFalse(fresh_session(None))
    def test_price_validation(self):
        self.assertIsNone(valid_price(0))
        self.assertIsNone(valid_price(float('nan')))
        self.assertEqual(valid_price('50.25'),50.25)

if __name__=='__main__':unittest.main()
