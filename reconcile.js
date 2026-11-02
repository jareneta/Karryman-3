/* Pure, local-only comparison; no network calls or persistence. */
(function(root){
'use strict';
function compare(local,imported){
 const current=Array.isArray(local?.positions)?local.positions:[];
 const incoming=Array.isArray(imported?.positions)?imported.positions:[];
 const byTicker=new Map(current.map(p=>[String(p.ticker||'').trim().toUpperCase(),p]));
 const next=new Set(incoming.map(p=>p.ticker));
 const added=[],removed=[],changed=[],unchanged=[];
 for(const p of incoming){
  const old=byTicker.get(p.ticker);
  if(!old){added.push(p.ticker);continue}
  const qtyChanged=Number(old.qty)!==Number(p.qty);
  const avgChanged=Number(old.avg)!==Number(p.avg);
  const lastChanged=Number(old.last)!==Number(p.last);
  if(qtyChanged||avgChanged||lastChanged)changed.push({ticker:p.ticker,quantity:qtyChanged,average:avgChanged,price:lastChanged});
  else unchanged.push(p.ticker);
 }
 for(const p of current){const t=String(p.ticker||'').trim().toUpperCase();if(t&&!next.has(t))removed.push(t)}
 return {added,removed,changed,unchanged,nlvChanged:Number(local?.nlv)!==Number(imported?.nlv),
  warning:'La importación sustituye posiciones y elimina stops; verificar datos antes de calcular riesgo.'};
}
root.KarrymanReconcile={compare};
if(typeof module==='object'&&module.exports)module.exports={compare};
})(typeof module==='object'&&module.exports?module.exports:window);
