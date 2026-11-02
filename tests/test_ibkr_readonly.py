import unittest
from unittest.mock import patch,MagicMock
from ibkr_readonly import IBKRReadOnly,sanitized_snapshot

class ReadOnlyIBKRTests(unittest.TestCase):
    def test_remote_endpoint_rejected(self):
        for url in ("https://example.com/v1/api","http://localhost:5000/v1/api",
                    "https://user:pass@localhost:5000/v1/api"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                IBKRReadOnly(url)
    def test_readonly_get_and_no_mutating_api(self):
        api=IBKRReadOnly()
        self.assertFalse(hasattr(api,"place_order"))
        self.assertFalse(hasattr(api,"cancel_order"))
        with patch("ibkr_readonly.urlopen") as mock:
            response=MagicMock()
            response.__enter__.return_value=response
            mock.return_value=response
            with patch("ibkr_readonly.json.load",return_value={"authenticated":True}):
                self.assertEqual(api.auth_status(),{"authenticated":True})
            request=mock.call_args.args[0]
            self.assertEqual(request.get_method(),"GET")
    def test_snapshot_has_no_account_id_and_unknown_stop(self):
        result=sanitized_snapshot({"netliquidation":{"amount":12000}},
            [{"contractDesc":"AAPL","position":3,"avgCost":100,"mktPrice":120,"accountId":"SECRET"}])
        self.assertEqual(result["nlv"],12000)
        self.assertEqual(result["positions"][0]["stop"],None)
        self.assertNotIn("accountId",str(result))

if __name__=="__main__":unittest.main()
