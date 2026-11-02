import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import review

class ReviewIntegrationTests(unittest.TestCase):
    def test_expired_fixed_watchlist_signal_is_not_proposed(self):
        old=(datetime.now(timezone.utc).date()-timedelta(days=10)).isoformat()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'setups.json').write_text(json.dumps({'candidates':[]}),encoding='utf-8')
            (root/'signals.json').write_text(json.dumps({'symbols':[{
                'ticker':'OLD','status':'senal','close':100,
                'stop_reference':95,'last_session':old,'setup':'base'
            }]}),encoding='utf-8')
            with patch.object(review,'DATA',root):
                review.main()
            report=json.loads((root/'review.json').read_text(encoding='utf-8'))
            self.assertEqual(report['review_count'],0)
            self.assertEqual(report['candidates'],[])
            self.assertFalse(report['orders_enabled'])
    def test_fresh_fixed_signal_is_preliminary_only(self):
        today=datetime.now(timezone.utc).date().isoformat()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'setups.json').write_text('{"candidates":[]}',encoding='utf-8')
            (root/'signals.json').write_text(json.dumps({'symbols':[{
                'ticker':'NEW','status':'senal','close':100,
                'stop_reference':95,'last_session':today,'setup':'base'
            }]}),encoding='utf-8')
            with patch.object(review,'DATA',root):
                review.main()
            report=json.loads((root/'review.json').read_text(encoding='utf-8'))
            self.assertEqual(report['review_count'],1)
            self.assertEqual(report['candidates'][0]['status'],'PRELIMINAR')
            self.assertFalse(report['candidates'][0]['technical_a_plus'])
            self.assertFalse(report['candidates'][0]['order_enabled'])

if __name__=='__main__':unittest.main()
