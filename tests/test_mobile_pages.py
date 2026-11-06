"""Static integration checks for the mobile pages.

Ensures deployment will not silently omit required local JavaScript modules.
No browser, account data, or network is needed.
"""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class MobilePageTests(unittest.TestCase):
    def test_local_scripts_exist(self):
        for page in ('index.html','cartera.html','review.html','manual_order.html'):
            html=(ROOT/page).read_text(encoding='utf-8')
            for src in re.findall(r'<script\s+[^>]*src=["\']([^"\']+)["\']',html):
                with self.subTest(page=page,src=src):
                    if src.startswith(('http:','https:','//')):
                        continue
                    self.assertTrue((ROOT/src.split('?')[0]).is_file(),f'{page}: missing {src}')
    def test_all_pages_share_brand_and_navigation(self):
        for page in sorted(ROOT.glob('*.html')):
            html=page.read_text(encoding='utf-8')
            with self.subTest(page=page.name):
                self.assertIn('href="karryman.css"',html)
                self.assertIn('src="karryman-nav.js"',html)
                self.assertRegex(html,r'<body[^>]*data-page="(hoy|cartera|escaner|mas)"')
        for asset in ('karryman.css','karryman-nav.js','karryman-icon.svg','mas.html'):
            self.assertTrue((ROOT/asset).is_file(),asset)
    def test_ibkr_import_accepts_any_file_name(self):
        html=(ROOT/'virtual.html').read_text(encoding='utf-8')
        self.assertIn('<input id="ibkrFile" type="file">',html)  # IBKR en móvil guarda .plain/.txt
        self.assertIn("$('ibkrFile').addEventListener('change',importFile)",html)
        self.assertIn('id="ibkrText"',html)
        self.assertIn('Es un PDF',html)
    def test_review_uses_local_only_paper_ledger(self):
        html=(ROOT/'review.html').read_text(encoding='utf-8')
        self.assertIn('paper_ledger.js',html)
        self.assertIn('KarrymanPaperLedger.save(localStorage,ticket)',html)
        self.assertIn('BORRADOR', (ROOT/'paper_ledger.js').read_text(encoding='utf-8'))
        self.assertNotIn('ibkr.com/v1/api',html.lower())
    def test_preliminary_signals_cannot_create_paper_draft(self):
        html=(ROOT/'review.html').read_text(encoding='utf-8')
        self.assertIn('b.disabled=x.technical_a_plus!==true',html)
        self.assertIn("if(x.technical_a_plus!==true)throw Error",html)
        self.assertIn('Sin dimensionamiento: señal preliminar',html)
    def test_review_displays_no_broker_connection_claim(self):
        html=(ROOT/'review.html').read_text(encoding='utf-8')
        self.assertIn('IBKR no conectado',html)
        self.assertIn('No se envían órdenes',html)

if __name__=='__main__':unittest.main()
