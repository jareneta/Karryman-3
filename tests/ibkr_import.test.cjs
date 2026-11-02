const assert=require('node:assert/strict');
const {test}=require('node:test');
const {normalize}=require('../ibkr_import.js');
test('valid IBKR snapshot strips unverified stops',()=>{
 const p=normalize({nlv:10000,positions:[{ticker:'AAPL',qty:3,avg:100,last:120,stop:90}]});
 assert.equal(p.nlv,'10000');assert.equal(p.positions[0].stop,'');
});
test('reject invalid positions and duplicates',()=>{
 assert.throws(()=>normalize({nlv:100,positions:[{ticker:'AAPL',qty:1,avg:10,last:11},{ticker:'AAPL',qty:1,avg:10,last:11}]}));
 assert.throws(()=>normalize({nlv:100,positions:[{ticker:'AAPL',qty:-1,avg:10,last:11}]}));
 assert.throws(()=>normalize({nlv:0,positions:[]}));
});
