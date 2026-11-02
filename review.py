"""Karryman 4.0: weekly public-data watchlist review. No broker access or orders."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA = Path("data")
def read(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

def valid_price(x):
    try:
        v = float(x)
        return v if 0 < v < 1e7 else None
    except (TypeError, ValueError):
        return None

def fresh_session(value, days=5):
    try:
        day=datetime.fromisoformat(str(value)).date()
        return timedelta(0)<=datetime.now(timezone.utc).date()-day<=timedelta(days=days)
    except (ValueError, TypeError):
        return False

def main():
    setups = read("setups.json")
    signals = read("signals.json")
    result = []
    for x in setups.get("candidates", []):
        close, stop = valid_price(x.get("close")), valid_price(x.get("stop_reference"))
        if not close or not stop or stop >= close or not fresh_session(x.get('last_session')):
            continue
        technical = x.get("technical_a_plus") is True
        fundamentals = x.get("fundamental_status") == "CUMPLE"
        result.append({
            "ticker": x.get("ticker"), "source": "Setups",
            "last_session": x.get("last_session"), "pattern": x.get("setup"),
            "status": "REVISAR_A_PLUS" if technical else "VIGILAR",
            "technical_a_plus": technical, "fundamentals_verified": fundamentals,
            "entry_reference": close, "stop_reference": stop,
            "target_2r_reference": round(close + 2 * (close - stop), 2),
            "risk_per_share": round(close - stop, 2),
            "risk_pct": round(100 * (close - stop) / close, 2),
            "rs_vs_spy_3m_pct": x.get("rs_vs_spy_3m_pct"),
            "pending_checks": ["Validar cierre y vigencia", "Resultados y noticias", "Fundamentales", "Riesgo agregado y cartera", "Aprobación humana"],
            "order_enabled": False
        })
    existing = {x["ticker"] for x in result}
    for x in signals.get("symbols", []):
        ticker = x.get("ticker")
        if x.get("status") != "senal" or ticker in existing:
            continue
        close, stop = valid_price(x.get("close")), valid_price(x.get("stop_reference"))
        if not close or not stop or stop >= close:
            continue
        result.append({
            "ticker": ticker, "source": "Lista fija", "last_session": x.get("last_session"),
            "pattern": x.get("setup"), "status": "PRELIMINAR",
            "technical_a_plus": False, "fundamentals_verified": False,
            "entry_reference": close, "stop_reference": stop,
            "target_2r_reference": round(close + 2 * (close - stop), 2),
            "risk_per_share": round(close - stop, 2),
            "risk_pct": round(100 * (close - stop) / close, 2),
            "pending_checks": ["Validación A+ completa", "Resultados y noticias", "Fundamentales", "Riesgo agregado y cartera", "Aprobación humana"],
            "order_enabled": False
        })
    result.sort(key=lambda x: (x["status"] != "REVISAR_A_PLUS", x["status"] != "PRELIMINAR", -(x.get("rs_vs_spy_3m_pct") or -999)))
    payload = {
        "schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "setups_generated_utc": setups.get("generated_utc"),
        "signals_generated_utc": signals.get("generated_utc"),
        "review_count": len(result),
        "technical_a_plus_count": sum(x["technical_a_plus"] for x in result),
        "broker_connected": False, "orders_enabled": False,
        "portfolio_analyzed": False,
        "freshness_policy": "Solo sesiones con antigüedad máxima de 5 días naturales; no se muestran referencias históricas caducadas.",
        "notes": "Referencias informativas basadas en cierres históricos. No hay verificación completa de fundamentales, earnings, stops de cartera ni ejecución de órdenes. No publicar datos IBKR.",
        "candidates": result
    }
    DATA.mkdir(exist_ok=True)
    (DATA / "review.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Revisión: {len(result)} candidatas, {payload['technical_a_plus_count']} A+ técnicas")

if __name__ == "__main__":
    main()
