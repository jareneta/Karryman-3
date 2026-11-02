/* Paper-only order tickets: no broker calls, no network, no execution. */
(function(root){
 'use strict';
 function create(proposal,portfolio,now=new Date().toISOString()){
   if(!root.KarrymanRisk)throw Error('Motor de riesgo no disponible');
   const risk=root.KarrymanRisk.assess(portfolio,proposal,1,5);
   if(!risk.eligible)throw Error('Propuesta bloqueada: '+risk.errors.join('; '));
   const ticker=String(proposal.ticker||'').trim().toUpperCase();
   if(!/^[A-Z]{1,5}$/.test(ticker))throw Error('Ticker no válido');
   const session=String(proposal.last_session||'');
   if(!/^\d{4}-\d{2}-\d{2}$/.test(session))throw Error('Fecha de cierre ausente');
   const age=(Date.parse(now.slice(0,10)+'T00:00:00Z')-Date.parse(session+'T00:00:00Z'))/86400000;
   if(!Number.isFinite(age)||age<0||age>5)throw Error('Cierre caducado o futuro');
   return Object.freeze({type:'SIMULACION_LOCAL',status:'BORRADOR_NO_ENVIADO',
     ticker,side:'BUY',quantity:risk.shares,reference_entry:risk.entry,
     reference_stop:risk.stop,estimated_risk_usd:Number(risk.newRisk.toFixed(2)),
     estimated_portfolio_risk_pct:Number(risk.aggregateRiskPct.toFixed(3)),
     signal_session:session,created_utc:now,
     warning:'No es una orden ni precio ejecutable. Revalidar cotización, cartera y stops antes de operar.'});
 }
 root.KarrymanPaper={create};
})(typeof window!=='undefined'?window:globalThis);
