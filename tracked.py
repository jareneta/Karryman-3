"""Guarda en data/tracked.json SOLO los tickers de tus posiciones (sin cantidades)."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TICKER = re.compile(r'^[A-Z][A-Z.\-]{0,9}$')


def parse(raw):
    items = re.split(r'[\s,;]+', str(raw or '').upper())
    return sorted({t for t in items if TICKER.match(t)})[:60]


def main(raw):
    tickers = parse(raw)
    Path('data').mkdir(exist_ok=True)
    Path('data/tracked.json').write_text(json.dumps(
        {'tickers': tickers, 'updated_utc': datetime.now(timezone.utc).isoformat(),
         'notes': 'Solo tickers para revisar posiciones; sin cantidades, precios ni patrimonio.'},
        ensure_ascii=False, indent=2), encoding='utf-8')
    print('Tickers seguidos:', len(tickers))


if __name__ == '__main__':
    main(' '.join(sys.argv[1:]))
