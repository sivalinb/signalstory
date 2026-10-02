const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const M = require('../signalstory/components/concept/math.js');

test('rate and irate respond differently to the same last-interval burst', () => {
  const r = M.rateExample(60);
  assert.deepEqual(r.values, [100,110,120,130,190]);
  assert.equal(r.rate, 1.5);
  assert.equal(r.irate, 4);
  assert.equal(r.increase, 112.5);
  assert.equal(M.rateExample(0).rate, .5);
  assert.equal(M.rateExample(0).irate, 0);
  assert.equal(M.rateExample(80).irate - r.irate, 4*(M.rateExample(80).rate-r.rate));
});
test('a restarted counter contributes its new value, never a negative event count', () => {
  assert.equal(M.counterChange([100,115,5,20,35]), 50);
  assert.equal(M.counterChange([9,0,2,0,3]),5);
});
test('one observation increments every fitting cumulative bucket, including its exact boundary', () => {
  assert.deepEqual(M.buckets([.12,.42,.8,1.4]),[0,2,3,4]);
  assert.deepEqual(M.buckets([.1,.5,1]),[1,2,3,3]);
  assert.deepEqual(M.buckets([]),[0,0,0,0]);
});
test('over-time functions answer distinct questions about the same samples', () => {
  const values=[2,4,6];
  for(const [fn,expected] of Object.entries({sum_over_time:12,avg_over_time:4,min_over_time:2,max_over_time:6,count_over_time:3}))assert.equal(M.overTime(values,fn),expected);
  assert.equal(M.overTime([2,4,0],'min_over_time'),0);
  assert.equal(M.overTime([2,4,12],'avg_over_time'),6);
  assert.ok(Number.isNaN(M.overTime([],'avg_over_time')));
});
test('a percentile interpolates inside its containing bucket, not across all counts', () => {
  assert.equal(M.quantile(.95).value,1.5);
  assert.equal(M.quantile(.90).value,1);
  assert.equal(M.quantile(.50).value,.4);
  assert.equal(M.quantile(.99).value,1.9);
});

test('every authored animation can draw every step with finite canvas coordinates', () => {
  // An isolated renderer unit harness, not a browser. Catch blank or invalid illustrations.
  const elements = new Map();
  const canvas = new Proxy({}, {get(_,name) {
    return (...args) => {for(const arg of args)if(typeof arg==='number')assert.ok(Number.isFinite(arg),`${name}: non-finite coordinate`);};
  },set(){return true;}});
  const el = id => {if(!elements.has(id))elements.set(id,{value:'6',textContent:'',getContext:()=>canvas,setAttribute(){}});return elements.get(id);};
  const window = {AcademyMath:M,matchMedia:()=>({matches:true}),parent:{postMessage(){}},addEventListener(){}};
  const context = vm.createContext({window,document:{getElementById:el,querySelector:()=>el('shell'),body:{scrollHeight:800}},ResizeObserver:class {observe(){}},requestAnimationFrame(){},cancelAnimationFrame(){},console});
  vm.runInContext(fs.readFileSync('signalstory/components/concept/lesson.js','utf8'),context);
  const levels = JSON.parse(fs.readFileSync('content/course.json','utf8')).missions.filter(m=>m.kind==='promql');
  const supported = vm.runInContext('SUPPORTED_KINDS',context);
  for(const level of levels)for(const lesson of level.concepts){
    assert.ok(supported.includes(lesson.animation.kind),lesson.id);
    context.payload=lesson.animation;
    for(let step=0;step<5;step++){
      context.step=step;
      vm.runInContext("data=payload;target=pos=step;var cfg2=config(data.kind);if(cfg2)$('knob').value=cfg2.value;$('function').value='sum_over_time';draw();",context);
      assert.ok(el('formula').textContent.length>0,lesson.id);
      assert.ok(!/NaN|undefined/.test(el('formula').textContent),lesson.id);
    }
  }
});
