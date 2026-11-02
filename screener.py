"""Karryman: Stock Analysis-inspired primary screener; Finviz is secondary.
Uses cached Discovery candidates, not a full-market SA/Finviz API feed.
Unknown fields never silently pass. No trading orders.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

DATA=Path("data")
def number(x):
    try:
        v=float(x)
        return v if v==v and abs(v)!=float("inf") else None
    except (TypeError, ValueError):
        return None

def check(value, threshold, inclusive=False):
    n=number(value)
    return None if n is None else n>=threshold if inclusive else n>threshold

def evaluate(x):
    checks={
        "price_over_5":check(x.get("close"),5,True),
        "average_volume_over_500k":check(x.get("avg_volume"),500000,True),
        "market_cap_over_300m":check(x.get("market_cap"),300000000),
        "return_3m_over_10":check(x.get("return_3m_pct"),10),
        "return_6m_over_10":check(x.get("return_6m_pct"),10),
        "return_1y_over_10":check(x.get("return_12m_pct"),10),
        "within_15pct_52w_high":None if number(x.get("distance_high_pct")) is None else number(x["distance_high_pct"])<15,
        "above_ma50":None if number(x.get("close")) is None or number(x.get("ma50")) is None else number(x["close"])>number(x["ma50"]),
        "above_ma200":None if number(x.get("close")) is None or number(x.get("ma200")) is None else number(x["close"])>number(x["ma200"]),
        "annual_revenue_growth_over_10":check(x.get("revenue_growth_pct"),10),
        "eps_over_minus_1":check(x.get("eps_ttm"),-1),
        # Not available reliably from Discovery; never assert that these pass.
        "zero_dividend_yield":None if number(x.get("dividend_yield")) is None else number(x["dividend_yield"])==0,
        "quarterly_revenue_growth_over_10":check(x.get("quarterly_revenue_growth_pct"),10),
        "quarterly_revenue_growth_comparison_over_10":None,
        "revenue_growth_this_year_over_10":None,
        "above_ma20":None if number(x.get("close")) is None or number(x.get("ma20")) is None else number(x["close"])>number(x["ma20"]),
    }
    # Finviz is only a complementary signal, not an entry gate.
    finviz_support=x.get("finviz_proxy") is True
    return {
        "ticker":x.get("ticker"),"last_session":x.get("last_session"),
        "close":x.get("close"),"category":x.get("category"),
        "checks":checks,
        "passed":sum(v is True for v in checks.values()),
        "failed":[k for k,v in checks.items() if v is False],
        "unverified":[k for k,v in checks.items() if v is None],
        "stock_analysis_status":"DESCARTADA" if False in checks.values() else "PENDIENTE_VERIFICACION" if None in checks.values() else "CUMPLE",
        "finviz_complement":finviz_support,
        "technical_score":x.get("score_preliminar"),
        "order_enabled":False,
    }

def main():
    source=DATA/"discovery.json"
    data=json.loads(source.read_text(encoding="utf-8"))
    items=[evaluate(x) for x in data.get("candidates",[]) if x.get("ticker")]
    eligible=[x for x in items if x["stock_analysis_status"]!="DESCARTADA"]
    eligible.sort(key=lambda x:(not x["finviz_complement"],-x["passed"],-(number(x["technical_score"]) or 0)))
    payload={
        "schema_version":1,"generated_utc":datetime.now(timezone.utc).isoformat(),
        "discovery_generated_utc":data.get("generated_utc"),
        "source":"Discovery cached Yahoo Finance data; approximation, not Stock Analysis/Finviz API",
        "universe_scanned_this_run":data.get("scanned_this_run"),
        "discovery_candidates":len(items),
        "primary_candidates":len(eligible),
        "complete_verified_matches":sum(x["stock_analysis_status"]=="CUMPLE" for x in eligible),
        "notes":"No se ha reproducido todavía el screener completo de Stock Analysis. Solo se filtran candidatas Discovery. Los campos no disponibles se marcan pendientes; métricas de crecimiento pueden tener definiciones distintas a Stock Analysis; nunca se asumen cumplidos. Finviz solo ordena como complemento. No hay órdenes.",
        "candidates":eligible[:100],
        "orders_enabled":False,
    }
    (DATA/"screener.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Discovery",len(items),"preseleccionadas",len(eligible),"verificadas",payload["complete_verified_matches"])

if __name__=="__main__":main()
