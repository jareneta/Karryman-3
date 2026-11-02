/* Private device-only draft ledger. No network, broker, or executable orders. */
(function(root){
'use strict';
const KEY='karryman_paper_drafts_v1';
function validate(ticket){
 if(!ticket||ticket.type!=='SIMULACION_LOCAL'||ticket.status!=='BORRADOR_NO_ENVIADO'
   ||ticket.side!=='BUY'||!/^[A-Z]{1,5}$/.test(ticket.ticker||'')
   ||!Number.isInteger(ticket.quantity)||ticket.quantity<=0
   ||!Number.isFinite(ticket.reference_entry)||ticket.reference_entry<=0
   ||!Number.isFinite(ticket.reference_stop)||ticket.reference_stop<=0
   ||ticket.reference_stop>=ticket.reference_entry
   ||!/^\d{4}-\d{2}-\d{2}$/.test(ticket.signal_session||''))
   throw Error('Borrador no válido');
 return true;
}
function read(storage){
 try{const data=JSON.parse(storage.getItem(KEY)||'[]');return Array.isArray(data)?data.filter(x=>{try{return validate(x)}catch{return false}}).slice(-100):[]}
 catch{return []}
}
function save(storage,ticket){
 validate(ticket);
 const all=read(storage);
 if(all.some(x=>x.ticker===ticket.ticker&&x.signal_session===ticket.signal_session))
   throw Error('Ya existe un borrador de este ticker y sesión');
 const next=[...all,ticket].slice(-100);
 storage.setItem(KEY,JSON.stringify(next));
 return next;
}
function clear(storage){storage.removeItem(KEY)}
root.KarrymanPaperLedger={read,save,clear};
if(typeof module==='object'&&module.exports)module.exports={read,save,clear};
})(typeof window!=='undefined'?window:globalThis);
