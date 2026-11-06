/* Local-only portfolio risk calculations. Never send positions to GitHub. */
(function(root){
  'use strict';
  const finite=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):null;
  function assess(portfolio,proposal,percent=1,aggregateLimitPct=5){
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
    // El margen no bloquea: solo se avisa. El tamaño lo limitan el riesgo (y el peso en trade_manager).
    const cash=finite(portfolio?.cash);
    const warnings=[];
    if(cash===null)warnings.push('Efectivo no verificado');
    if(cash!==null&&cash<0)warnings.push('Efectivo negativo: ya estás usando margen ('+cash.toFixed(2)+' $)');
    const duplicate=positions.some(p=>String(p.ticker||'').toUpperCase()===String(proposal?.ticker||'').toUpperCase());
    if(duplicate)errors.push('Ticker ya presente en cartera; requiere evaluación agregada');
    const riskPerShare=entry-stop;
    const cap=finite(aggregateLimitPct);
    if(!(cap>0&&cap<=100))errors.push('Límite de riesgo agregado inválido');
    if(nlv>0&&cap!==null&&existingRisk>nlv*cap/100)errors.push('La cartera ya supera el límite de riesgo agregado');
    const remainingRisk=nlv>0&&cap!==null?Math.max(0,nlv*cap/100-existingRisk):0;
    const maxByRisk=errors.length===0?Math.floor(Math.min(nlv*riskPct/100,remainingRisk)/riskPerShare):0;
    const shares=Math.max(0,maxByRisk);
    const marginUsed=cash===null?null:Math.max(0,shares*(entry||0)-Math.max(0,cash));
    if(shares>0&&marginUsed>0)warnings.push('Esta compra usaría unos '+marginUsed.toFixed(2)+' $ de margen');
    return {shares,entry,stop,riskPerShare:Number.isFinite(riskPerShare)?riskPerShare:null,
      positionValue:shares*(entry||0),newRisk:shares*(riskPerShare||0),
      aggregateLimitPct:cap,remainingRisk,existingRisk,aggregateRisk:existingRisk+shares*(riskPerShare||0),
      aggregateRiskPct:nlv>0?100*(existingRisk+shares*(riskPerShare||0))/nlv:null,
      exposure,unknownStops:unknown,eligible:errors.length===0&&shares>0,
      errors:shares===0&&errors.length===0?['Capital insuficiente para una acción al riesgo permitido']:errors,
      warnings,marginUsed,
      orderEnabled:false};
  }
  root.KarrymanRisk={assess};
})(typeof window!=='undefined'?window:globalThis);
