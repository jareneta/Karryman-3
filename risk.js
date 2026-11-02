/* Local-only portfolio risk calculations. Never send positions to GitHub. */
(function(root){
  'use strict';
  const finite=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):null;
  function assess(portfolio,proposal,percent=1){
    const nlv=finite(portfolio?.nlv),entry=finite(proposal?.entry_reference),stop=finite(proposal?.stop_reference);
    const positions=Array.isArray(portfolio?.positions)?portfolio.positions:[];
    const riskPct=Math.min(1,Math.max(0,finite(percent)??1));
    const errors=[];
    if(!(nlv>0))errors.push('Falta patrimonio neto válido');
    if(!(entry>0&&stop>0&&stop<entry))errors.push('Entrada/stop no válidos');
    let existingRisk=0,unknown=0,exposure=0;
    for(const p of positions){
      const qty=finite(p.qty),last=finite(p.last),ps=finite(p.stop);
      if(!(qty>0&&last>0)){unknown++;continue}
      exposure+=qty*last;
      if(!(ps>0&&ps<last)){unknown++;continue}
      existingRisk+=qty*(last-ps);
    }
    if(unknown)errors.push(unknown+' posiciones sin datos/stop válido');
    const cash=finite(portfolio?.cash);
    if(cash===null)errors.push('Efectivo no disponible');
    if(cash!==null&&cash<0)errors.push('Efectivo negativo / margen en uso');
    const duplicate=positions.some(p=>String(p.ticker||'').toUpperCase()===String(proposal?.ticker||'').toUpperCase());
    if(duplicate)errors.push('Ticker ya presente en cartera; requiere evaluación agregada');
    const riskPerShare=entry-stop;
    const maxByRisk=errors.length===0?Math.floor(nlv*riskPct/100/riskPerShare):0;
    const maxByCash=errors.length===0?Math.floor(Math.max(0,cash)/entry):0;
    const shares=Math.max(0,Math.min(maxByRisk,maxByCash));
    return {shares,entry,stop,riskPerShare:Number.isFinite(riskPerShare)?riskPerShare:null,
      positionValue:shares*(entry||0),newRisk:shares*(riskPerShare||0),
      existingRisk,aggregateRisk:existingRisk+shares*(riskPerShare||0),
      aggregateRiskPct:nlv>0?100*(existingRisk+shares*(riskPerShare||0))/nlv:null,
      exposure,unknownStops:unknown,eligible:errors.length===0&&shares>0,
      errors:shares===0&&errors.length===0?['Capital insuficiente para una acción al riesgo permitido']:errors,
      orderEnabled:false};
  }
  root.KarrymanRisk={assess};
})(typeof window!=='undefined'?window:globalThis);
