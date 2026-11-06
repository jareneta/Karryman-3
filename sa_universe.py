"""Guarda en data/universe.json la lista de tickers de tu screener de Stock Analysis.
Solo tickers (es el resultado de un screener público, no datos de tu cuenta)."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TICKER = re.compile(r'^[A-Z][A-Z.\-]{0,9}$')


def parse(raw, limit=2500):
    items = re.split(r'[\s,;]+', str(raw or '').upper())
    return sorted({t for t in items if TICKER.match(t)})[:limit]


def main(raw):
    tickers = parse(raw)
    if not tickers:
        raise SystemExit('Lista vacía: no se modifica el universo')
    Path('data').mkdir(exist_ok=True)
    Path('data/universe.json').write_text(json.dumps(
        {'source': 'Stock Analysis (exportación del screener del usuario)', 'tickers': tickers,
         'updated_utc': datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=1), encoding='utf-8')
    print('Universo Stock Analysis:', len(tickers), 'tickers')


if __name__ == '__main__':
    main(' '.join(sys.argv[1:]))
