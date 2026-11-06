/* Karryman · cabecera con logo y barra de navegación inferior comunes.
   Uso: <body data-page="hoy|cartera|escaner|mas" data-title="Título de la página">
   y <script src="karryman-nav.js" defer></script>. Sin datos ni red. */
(function(){
  'use strict';
  const body=document.body;if(!body||document.querySelector('.k-tabbar'))return;
  const page=body.dataset.page||'mas';
  const title=body.dataset.title||document.title.replace(/^Karryman\s*[·:-]?\s*/,'')||'Karryman';
  const icon={
    hoy:'<svg viewBox="0 0 24 24"><path d="M3 12h4l3 8 4-16 3 8h4"/></svg>',
    cartera:'<svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/></svg>',
    escaner:'<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    mas:'<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></svg>'
  };
  const tabs=[['hoy','plan.html','Hoy'],['cartera','virtual.html','Cartera'],['escaner','index.html','Escáner'],['mas','mas.html','Más']];
  const header=document.createElement('header');header.className='k-header';
  header.innerHTML='<a class="k-home" href="plan.html" aria-label="Karryman: ir a Hoy"><img src="karryman-icon.svg" alt="" width="40" height="40"><span class="k-brand"><span class="k-word">Karryman <span>4.0</span></span><span class="k-page"></span></span></a>';
  header.querySelector('.k-page').textContent=title;
  body.insertBefore(header,body.firstChild);
  const nav=document.createElement('nav');nav.className='k-tabbar';nav.setAttribute('aria-label','Secciones');
  nav.innerHTML=tabs.map(([id,href,label])=>'<a href="'+href+'"'+(id===page?' class="on" aria-current="page"':'')+'>'+icon[id]+'<span>'+label+'</span></a>').join('');
  body.appendChild(nav);
  if(!document.querySelector('meta[name=theme-color]')){const m=document.createElement('meta');m.name='theme-color';document.head.appendChild(m)}
  document.querySelector('meta[name=theme-color]').content='#f4f6f0';
  // Service worker solo para «Compartir → Karryman» (extracto IBKR). No cachea páginas.
  if('serviceWorker' in navigator&&location.protocol!=='file:'){navigator.serviceWorker.register('sw.js').catch(()=>{})}
})();
