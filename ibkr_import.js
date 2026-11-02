(function(root){
'use strict';
function finite(value){return typeof value==='number'&&Number.isFinite(value)}
function normalize(payload){
 if(!payload||typeof payload!=='object'||Array.isArray(payload))throw Error('Formato de cartera inválido');
 const positions=payload.positions;
 if(!Array.isArray(positions)||positions.length>150)throw Error('Posiciones inválidas o excesivas');
 const seen=new Set();
 const cleaned=positions.map(p=>{
   if(!p||typeof p!=='object')throw Error('Posición inválida');
   const ticker=String(p.ticker||'').trim().toUpperCase();
   if(!/^[A-Z][A-Z.\-]{0,9}$/.test(ticker)||seen.has(ticker))throw Error('Ticker duplicado o inválido');
   seen.add(ticker);
   const qty=Number(p.qty),avg=Number(p.avg),last=Number(p.last);
   if(!finite(qty)||qty<=0||!finite(avg)||avg<0||!finite(last)||last<=0)throw Error('Precio o cantidad inválidos');
   // Stops from an external snapshot are not trusted. Require manual verification.
   return {ticker,qty:String(qty),avg:String(avg),last:String(last),stop:''};
 });
 const nlv=Number(payload.nlv);
 if(!finite(nlv)||nlv<=0)throw Error('Falta NLV válido');
 return {nlv:String(nlv),positions:cleaned};
}
root.KarrymanImport={normalize};
})(typeof module==='object'&&module.exports?module.exports:window);
