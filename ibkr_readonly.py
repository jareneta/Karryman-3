"""Local-only IBKR Client Portal read-only adapter.

Runs on the USER'S computer next to an authenticated Client Portal Gateway.
Never exposes credentials, account details, or endpoints to GitHub Pages.
No order placement, cancellation or account mutation methods exist.
"""
import json
import os
import ssl
from urllib.request import Request, urlopen
from urllib.parse import urlparse

class IBKRReadOnly:
    def __init__(self,base_url="https://127.0.0.1:5000/v1/api",timeout=8,verify_tls=True):
        parsed=urlparse(base_url)
        if parsed.scheme!="https" or parsed.hostname not in ("localhost","127.0.0.1") or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("IBKR Gateway must be local HTTPS")
        self.base_url=base_url.rstrip("/")
        self.timeout=timeout
        self.context=ssl.create_default_context() if verify_tls else ssl._create_unverified_context()
    def _get(self,path):
        if not path.startswith("/") or ".." in path or "?" in path:
            raise ValueError("Invalid API path")
        request=Request(self.base_url+path,method="GET",headers={"Accept":"application/json"})
        with urlopen(request,timeout=self.timeout,context=self.context) as response:
            return json.load(response)
    def auth_status(self):
        return self._get("/iserver/auth/status")
    def accounts(self):
        return self._get("/portfolio/accounts")
    def summary(self,account_id):
        if not isinstance(account_id,str) or not account_id.isalnum():
            raise ValueError("Invalid account identifier")
        return self._get("/portfolio/"+account_id+"/summary")
    def positions(self,account_id,page=0):
        if not isinstance(account_id,str) or not account_id.isalnum() or not isinstance(page,int) or page<0 or page>100:
            raise ValueError("Invalid account or page")
        return self._get("/portfolio/"+account_id+"/positions/"+str(page))

def sanitized_snapshot(summary,positions):
    """Return minimum portfolio data for local-only display; no account ID."""
    nlv=summary.get("netliquidation",summary.get("NetLiquidation"))
    if isinstance(nlv,dict):nlv=nlv.get("amount")
    if not isinstance(positions,list):raise ValueError("Invalid positions payload")
    return {"nlv":nlv,"positions":[{"ticker":str(p.get("contractDesc",p.get("ticker",""))),
        "qty":p.get("position"),"avg":p.get("avgCost"),"last":p.get("mktPrice"),
        "stop":None} for p in positions]}
