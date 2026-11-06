const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');
const ctx={};ctx.globalThis=ctx;
vm.runInNewContext(fs.readFileSync('risk.js','utf8'),ctx);
vm.runInNewContext(fs.readFileSync('trade_manager.js','utf8'),ctx);
const T=ctx.KarrymanTrade;
const pos={ticker:'ABC',qty:9,avg:100,stop:90,initial_stop:90,entry_date:'2026-10-01',partial_done:false};
const q=(close,extra={})=>({last_session:'2026-11-05',high:close,low:close,close,ema10:close-1,ema20:close-3,ma50:close-8,bars:[],...extra});
// Stop por cierre
let m=T.manage(pos,q(89.5));assert.equal(m.action,'VENDER_TODO');assert.equal(m.sellQty,9);
// Entre stop y +2R
m=T.manage(pos,q(105));assert.equal(m.action,'MANTENER');assert.equal(m.target2r,120);assert.equal(m.rMultiple,0.5);
// +1R informativo, sin acción
m=T.manage(pos,q(111));assert.equal(m.action,'MANTENER');assert.ok(m.reasons.some(r=>r.includes('+1R')));
// +2R tocado intradía en una sesión pasada desde la entrada -> vender 1/3 y stop a breakeven
m=T.manage(pos,q(115,{bars:[['2026-09-20',130,95,96],['2026-10-20',121,110,118]]}));
assert.equal(m.action,'VENDER_PARCIAL');assert.equal(m.sellQty,3);assert.equal(m.newStop,100);
// Barras anteriores a la entrada no cuentan
m=T.manage(pos,q(115,{bars:[['2026-09-20',130,95,96]]}));assert.equal(m.action,'MANTENER');
// Runner: sale con cierre bajo EMA20
const runner={...pos,qty:6,stop:100,partial_done:true};
m=T.manage(runner,q(130,{ema20:131}));assert.equal(m.action,'VENDER_RUNNER');assert.equal(m.sellQty,6);
m=T.manage(runner,q(130,{ema20:125}));assert.equal(m.action,'MANTENER_RUNNER');assert.equal(m.newStop,125);
m=T.manage(runner,q(130,{ema10:131,ema20:125}),{trail:'ema10'});assert.equal(m.action,'VENDER_RUNNER');
m=T.manage(runner,q(99));assert.equal(m.action,'VENDER_TODO');
// Sin stop inicial o sin cotización no se inventa nada
assert.equal(T.manage({...pos,stop:null,initial_stop:null},q(105)).action,'REVISAR');
assert.equal(T.manage(pos,null).action,'REVISAR');
// Tamaños parciales
assert.equal(T.partialQty(1,1/3),1);assert.equal(T.partialQty(2,1/3),1);assert.equal(T.partialQty(10,1/3),3);
assert.equal(T.manage({...pos,qty:1},q(121)).action,'VENDER_TODO');
// Tamaño de entrada: 1% riesgo, 6% total, 20% peso
const pf={nlv:10000,cash:10000,positions:[]};
let s=T.sizeEntry(pf,{ticker:'XYZ',entry_reference:50,stop_reference:48});
assert.equal(s.shares,40);assert.ok(s.limitedByWeight);assert.equal(s.weightPct,20);assert.equal(s.newRisk,80);
s=T.sizeEntry(pf,{ticker:'XYZ',entry_reference:50,stop_reference:45});assert.equal(s.shares,20);assert.equal(s.newRiskPct,1);
const loaded={nlv:10000,cash:10000,positions:[{ticker:'A',qty:100,last:50,stop:44.5}]};
s=T.sizeEntry(loaded,{ticker:'XYZ',entry_reference:50,stop_reference:45});assert.equal(s.shares,10);assert.ok(s.aggregateRiskPct<=6);
const mg=T.sizeEntry({...pf,cash:-5},{ticker:'XYZ',entry_reference:50,stop_reference:45});
assert.equal(mg.eligible,true);assert.equal(mg.shares,20);assert.equal(mg.marginUsed,1000);
assert.ok(mg.warnings.some(w=>w.includes('margen')));
assert.equal(s.orderEnabled,false);
assert.ok(T.orderTicket({ticker:'XYZ',max_entry_price:52.5,stop_reference:45,target_2r:60},s).startsWith('COMPRAR 10 XYZ'));
// El máximo del propio día de entrada no cuenta (pudo ser antes de comprar)
const sameDay={...pos,entry_date:'2026-11-05'};
m=T.manage(sameDay,q(101,{last_session:'2026-11-05',high:130,bars:[['2026-11-05',130,95,101]]}));
assert.equal(m.action,'MANTENER');
m=T.manage(sameDay,q(118,{last_session:'2026-11-06',high:121,bars:[['2026-11-05',130,95,101],['2026-11-06',121,110,118]]}));
assert.equal(m.action,'VENDER_PARCIAL');
console.log('Trade manager tests passed');
