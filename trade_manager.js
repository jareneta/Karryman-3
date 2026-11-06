/* Karryman: gestión de posiciones y propuestas de entrada. Solo en el navegador.
   Reglas: stop por cierre · +2R vender 1/3 y subir stop del resto a breakeven ·
   runner: vender con cierre bajo la media elegida (EMA20 por defecto).
   Nunca envía órdenes: todo son propuestas que el usuario aprueba o descarta. */
(function(root){
  'use strict';
  const num=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):null;
  const DEFAULT_RULES={riskPct:1,totalRiskPct:6,maxWeightPct:20,partialFraction:1/3,trail:'ema20'};
  const round2=x=>Math.round(x*100)/100;

  function partialQty(qty,fraction){
    if(qty<=1)return qty;
    return Math.min(qty-1,Math.max(1,Math.round(qty*fraction)));
  }

  /* position: {ticker,qty,avg,stop,initial_stop,partial_done,entry_date}
     quote: {last_session,high,low,close,ema10,ema20,ma50,bars:[[date,high,low,close]]} */
  function manage(position,quote,rules){
    const r={...DEFAULT_RULES,...(rules||{})};
    const qty=num(position?.qty),avg=num(position?.avg);
    const stop=num(position?.stop),initial=num(position?.initial_stop)??stop;
    const out={ticker:String(position?.ticker||'').toUpperCase(),action:'REVISAR',severity:'warn',reasons:[],orderEnabled:false};
    if(!(qty>0&&avg>0)){out.reasons.push('Faltan cantidad o precio medio');return out}
    if(!quote||num(quote.close)===null){out.reasons.push('Sin cotización publicada: ejecuta el análisis o introduce el precio en Cartera');return out}
    const close=num(quote.close),low=num(quote.low);
    out.close=close;out.session=quote.last_session;
    out.pnl=round2(qty*(close-avg));
    if(!(initial>0&&initial<avg)){
      out.reasons.push('Define el stop inicial (por debajo del precio medio) para calcular R');
      return out;
    }
    const R=avg-initial;
    out.R=round2(R);out.rMultiple=round2((close-avg)/R);
    out.target1r=round2(avg+R);out.target2r=round2(avg+2*R);
    const activeStop=stop>0?stop:initial;
    out.stop=activeStop;
    // Máximo DESPUÉS del día de entrada: el máximo de ese mismo día puede ser anterior a la compra.
    // Sin fecha de entrada solo se usa la última sesión.
    const bars=Array.isArray(quote.bars)?quote.bars:[];
    const entryDate=position.entry_date||null;
    const since=entryDate?bars.filter(b=>b[0]>entryDate):bars.slice(-1);
    const lastCounts=!entryDate||String(quote.last_session||'')>entryDate;
    const maxHigh=Math.max(close,lastCounts?(num(quote.high)??close):close,...since.map(b=>num(b[1])??-Infinity));
    out.maxHigh=round2(maxHigh);
    if(close<=activeStop){
      return {...out,action:'VENDER_TODO',severity:'bad',sellQty:qty,
        reasons:['Cierre '+close+' en o bajo el stop '+activeStop+': salir en la próxima apertura']};
    }
    if(low!==null&&low<=activeStop)out.reasons.push('El mínimo del día tocó el stop; si tenías orden stop en IBKR pudo ejecutarse');
    if(!position.partial_done){
      if(maxHigh>=avg+2*R){
        const sell=partialQty(qty,r.partialFraction);
        return {...out,action:sell===qty?'VENDER_TODO':'VENDER_PARCIAL',severity:'good',sellQty:sell,
          newStop:round2(Math.max(activeStop,avg)),
          reasons:[...out.reasons,'+2R alcanzado ('+out.target2r+'): vender '+sell+' de '+qty+' acciones y subir el stop del resto a breakeven ('+round2(Math.max(activeStop,avg))+')']};
      }
      if(maxHigh>=avg+R)out.reasons.push('+1R alcanzado ('+out.target1r+'); siguiente objetivo +2R '+out.target2r);
      return {...out,action:'MANTENER',severity:'ok',reasons:[...out.reasons,'Objetivo +2R: '+out.target2r+' · stop por cierre: '+activeStop]};
    }
    // Runner: tras la venta parcial, sale con cierre bajo la media elegida.
    const trailValue=num(quote[r.trail]);
    out.trail=r.trail;out.trailValue=trailValue;
    if(trailValue!==null&&close<trailValue){
      return {...out,action:'VENDER_RUNNER',severity:'bad',sellQty:qty,
        reasons:[...out.reasons,'Runner: cierre '+close+' bajo '+r.trail.toUpperCase()+' '+trailValue+': vender el resto']};
    }
    const suggested=trailValue!==null?round2(Math.max(activeStop,avg,Math.min(trailValue,close))):activeStop;
    const res={...out,action:'MANTENER_RUNNER',severity:'ok',
      reasons:[...out.reasons,'Runner vivo: sale con cierre bajo '+r.trail.toUpperCase()+(trailValue!==null?' ('+trailValue+')':'')+' · stop mínimo '+round2(Math.max(activeStop,avg))]};
    if(suggested>activeStop)res.newStop=suggested;
    return res;
  }

  /* Tamaño de una entrada respetando riesgo por operación, riesgo total, peso y efectivo. */
  function sizeEntry(portfolio,entry,rules){
    const r={...DEFAULT_RULES,...(rules||{})};
    const risk=root.KarrymanRisk;
    const base=risk.assess(portfolio,{ticker:entry.ticker,entry_reference:entry.entry_reference,stop_reference:entry.stop_reference},r.riskPct,r.totalRiskPct);
    const nlv=num(portfolio?.nlv),price=num(entry.entry_reference);
    const maxByWeight=nlv>0&&price>0?Math.floor(nlv*r.maxWeightPct/100/price):0;
    const shares=Math.max(0,Math.min(base.shares,maxByWeight));
    const perShare=base.riskPerShare||0;
    const errors=[...base.errors];
    if(base.shares>shares&&shares>0)errors.push('Limitado por peso máximo '+r.maxWeightPct+'%');
    const cash=num(portfolio?.cash);
    const marginUsed=cash===null?null:round2(Math.max(0,shares*(price||0)-Math.max(0,cash)));
    const warnings=base.warnings.filter(w=>!/usaría unos/.test(w));
    if(shares>0&&marginUsed>0)warnings.push('Esta compra usaría unos '+marginUsed.toFixed(2)+' $ de margen');
    return {...base,shares,limitedByWeight:base.shares>shares,warnings,marginUsed,
      positionValue:round2(shares*(price||0)),newRisk:round2(shares*perShare),
      weightPct:nlv>0?round2(100*shares*(price||0)/nlv):null,
      newRiskPct:nlv>0?round2(100*shares*perShare/nlv):null,
      aggregateRisk:round2(base.existingRisk+shares*perShare),
      aggregateRiskPct:nlv>0?round2(100*(base.existingRisk+shares*perShare)/nlv):null,
      eligible:base.errors.length===0&&shares>0,errors:shares===0&&!errors.length?['Capital o límites insuficientes para 1 acción']:errors,
      orderEnabled:false};
  }

  function orderTicket(entry,size){
    if(!size||!(size.shares>0))return '';
    return 'COMPRAR '+size.shares+' '+entry.ticker+' · orden LMT a la apertura, máx. '+entry.max_entry_price+
      ' · STOP '+entry.stop_reference+' · +2R '+entry.target_2r+' (vender 1/3)';
  }

  root.KarrymanTrade={manage,sizeEntry,orderTicket,partialQty,DEFAULT_RULES};
})(typeof window!=='undefined'?window:globalThis);
