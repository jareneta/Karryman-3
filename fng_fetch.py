"""Karryman · descarga del historial del CNN Fear & Greed Index (endpoint público no oficial). Solo lectura.
Guarda fecha, valor y etiqueta; no se interpreta aquí."""
import json
import os
import sys
import urllib.request

URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/'
HDR = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
       'Accept': 'application/json', 'Origin': 'https://edition.cnn.com', 'Referer': 'https://edition.cnn.com/'}


def fetch(start):
    req = urllib.request.Request(URL + start, headers=HDR)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'data/v24_fng_historial.json'
    res = {'fuente': 'CNN production.dataviz.cnn.io (no oficial)'}
    for start in ('2011-01-01', '2015-01-01'):
        try:
            js = fetch(start)
            h = js['fear_and_greed_historical']['data']
            rows = [{'fecha': pd_date(x['x']), 'valor': round(float(x['y']), 2), 'etiqueta': x.get('rating')} for x in h]
            res.update({'inicio_pedido': start, 'n': len(rows), 'primera': rows[0]['fecha'], 'ultima': rows[-1]['fecha'], 'actual': js.get('fear_and_greed'), 'serie': rows})
            break
        except Exception as e:
            res.setdefault('errores', []).append(f'{start}: {str(e)[:150]}')
    print('RESUMEN_FNG ' + json.dumps({k: v for k, v in res.items() if k != 'serie'}, default=str), flush=True)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    json.dump(res, open(out_path, 'w'), default=str)


def pd_date(ms):
    import datetime
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')


if __name__ == '__main__':
    main()
