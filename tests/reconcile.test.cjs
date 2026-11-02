const assert=require('node:assert/strict');
const {test}=require('node:test');
const {compare}=require('../reconcile.js');
test('compares positions and net liquidation without mutating data',()=>{
 const local={nlv:'1000',positions:[{ticker:'AAPL',qty:'2',avg:'100',last:'110',stop:'90'},{ticker:'MSFT',qty:'1',avg:'200',last:'210',stop:'190'}]};
 const imported={nlv:'1100',positions:[{ticker:'AAPL',qty:'3',avg:'100',last:'115',stop:''},{ticker:'NVDA',qty:'1',avg:'120',last:'130',stop:''}]};
 const diff=compare(local,imported);
 assert.deepEqual(diff.added,['NVDA']);assert.deepEqual(diff.removed,['MSFT']);
 assert.deepEqual(diff.changed,[{ticker:'AAPL',quantity:true,average:false,price:true}]);
 assert.equal(diff.nlvChanged,true);assert.equal(local.positions[0].stop,'90');
});
test('unchanged positions do not trigger change',()=>{
 const x={nlv:100,positions:[{ticker:'QQQ',qty:1,avg:5,last:6}]};
 const diff=compare(x,x);assert.deepEqual(diff.unchanged,['QQQ']);assert.equal(diff.nlvChanged,false);
});
