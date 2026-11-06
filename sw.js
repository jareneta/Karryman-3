/* Karryman · service worker mínimo.
   Solo recibe el extracto de IBKR compartido desde Android («Compartir → Karryman»)
   y lo deja en este dispositivo para que Cartera lo importe. No guarda páginas
   en caché (siempre se carga la versión publicada) y no envía nada a ningún servidor. */
'use strict';
const SHARE_CACHE='karryman-share-v1';
const SHARE_KEY='./__shared-ibkr__';

self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));

self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='POST'||!url.pathname.endsWith('/share-target'))return;
  event.respondWith((async()=>{
    let text='';
    try{
      const form=await event.request.formData();
      const file=form.get('file');
      if(file&&typeof file.text==='function'){
        if(file.size>15*1024*1024)throw Error('too big');
        text=await file.text();
      }
      if(!text)text=String(form.get('text')||'');
    }catch(e){text=''}
    const cache=await caches.open(SHARE_CACHE);
    await cache.put(SHARE_KEY,new Response(text,{headers:{'Content-Type':'text/plain;charset=utf-8'}}));
    return Response.redirect(new URL('./virtual.html?shared=1',self.registration.scope).href,303);
  })());
});
