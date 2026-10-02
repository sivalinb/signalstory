/* First-party, lesson-specific drawings; no CDN, remote code, or learner HTML. */
'use strict';
const $ = id => document.getElementById(id), c = $('canvas').getContext('2d'), M = window.AcademyMath;
const C = {ink:'#edf2ff',muted:'#aabdd8',line:'#344865',orange:'#f4ca77',green:'#80f0ce',blue:'#88bbef',red:'#ff8eaa',purple:'#c7a8ff'};
const SUPPORTED_KINDS = ['sample','series','labels','counter','gauge','reset','observations','bucket_rule','buckets','hist_parts','vectors','filter','window','rate','rate_compare','increase','sum_time','average_time','extrema_time','gauge_change','axes','aggregate','ratio','matching','group_left','missing','quantile','hist_pipeline','representations','offset','pipeline','alert','cardinality','incident','budget','burn'];
let data=null, seenLesson=null, target=0, pos=0, playing=false, last=0, elapsed=0;
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
const fmt = value => Number(value.toFixed(3)).toString();
function post(type, extra={}) { window.parent.postMessage({isStreamlitMessage:true,type,...extra}, '*'); }
function height() { post('streamlit:setFrameHeight', {height:document.body.scrollHeight+5}); }
function text(t,x,y,size=17,color=C.ink,align='left') { c.fillStyle=color;c.font=`${size>=18?'650':'500'} ${size}px system-ui`;c.textAlign=align;c.fillText(t,x,y);c.textAlign='left'; }
function line(x,y,xx,yy,col=C.line,w=2) { c.beginPath();c.moveTo(x,y);c.lineTo(xx,yy);c.strokeStyle=col;c.lineWidth=w;c.stroke(); }
function box(x,y,w,h,label='',col=C.blue,alpha=1) { c.save();c.globalAlpha=alpha;c.shadowColor=col+'15';c.shadowBlur=18;c.fillStyle=col+'12';c.strokeStyle=col;c.lineWidth=1.5;c.beginPath();c.roundRect(x,y,w,h,12);c.fill();c.stroke();if(label)text(label,x+w/2,y+h/2+6,17,col,'center');c.restore(); }
function dot(x,y,r,col=C.orange) { c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fillStyle=col;c.fill(); }
function arrow(x,y,xx,yy,col=C.green) { line(x,y,xx,yy,col);const a=Math.atan2(yy-y,xx-x);c.beginPath();c.moveTo(xx,yy);c.lineTo(xx-9*Math.cos(a-.5),yy-9*Math.sin(a-.5));c.lineTo(xx-9*Math.cos(a+.5),yy-9*Math.sin(a+.5));c.closePath();c.fillStyle=col;c.fill(); }
function caption(t) { text(t,430,294,16,C.muted,'center'); }
function calc(formula,detail) { $('formula').textContent=formula;$('detail').textContent=detail; }
function nVisible(length) { return Math.min(length, Math.floor(pos)+1); }
function graph(values, labels, {x=80,y=68,w=510,h=162,col=C.orange,n=values.length,max=Math.max(...values)*1.2,min=0,annotate=true}={}) {
  line(x,y,x,y+h);line(x,y+h,x+w,y+h);text(fmt(max),x-12,y+5,13,C.muted,'right');text(fmt(min),x-12,y+h+5,13,C.muted,'right');
  const point=i=>[x+i*w/(values.length-1),y+h-(values[i]-min)/(max-min)*h];
  const count=Math.min(values.length,n);c.beginPath();for(let i=0;i<count;i++){const [xx,yy]=point(i);i?c.lineTo(xx,yy):c.moveTo(xx,yy);}c.strokeStyle=col;c.lineWidth=3;c.stroke();
  for(let i=0;i<values.length;i++){const [xx,yy]=point(i);if(i<count){dot(xx,yy,6,col);if(annotate)text(fmt(values[i]),xx,yy-14,16,col,'center');}if(labels)text(labels[i],xx,y+h+28,13,C.muted,'center');}
  if(n < values.length && n === nVisible(5)) {
    const phase=pos-Math.floor(pos),a=point(n-1),b=point(n);
    const xx=a[0]+(b[0]-a[0])*phase,yy=a[1]+(b[1]-a[1])*phase;
    line(a[0],a[1],xx,yy,col,3);dot(xx,yy,7,col);
  }
  return point;
}
function person(x,y,col=C.orange) { dot(x,y,6,col);line(x,y+9,x,y+30,col,5);line(x-9,y+17,x+9,y+17,col,4);line(x,y+29,x-7,y+42,col,4);line(x,y+29,x+7,y+42,col,4); }
function card(x,y,w,title,value,col=C.blue,sub='') { box(x,y,w,100,'',col);text(title,x+w/2,y+26,14,C.muted,'center');text(value,x+w/2,y+62,26,col,'center');if(sub)text(sub,x+w/2,y+84,12,C.muted,'center'); }
function pipeline(stages,s=target) { stages.forEach((item,i)=>{const x=28+i*167;box(x,90,146,116,'',i<=s?C.green:C.muted,i<=s?1:.35);text(String(i+1),x+20,116,14,C.orange);item.split('|').forEach((t,j)=>text(t,x+73,147+j*24,16,i===s?C.green:C.ink,'center'));if(i<4)arrow(x+149,150,x+165,150,i<s?C.green:C.line);}); }
function config(kind) {
  if(['rate','rate_compare','increase'].includes(kind))return {min:0,max:80,step:5,value:60,label:'Requests in the last 15 seconds',unit:'requests'};
  if(['sum_time','average_time','extrema_time'].includes(kind))return {min:0,max:12,step:1,value:6,label:'Last queue sample',unit:'people'};
  if(['buckets','hist_parts'].includes(kind))return {min:.6,max:2,step:.1,value:1.4,label:'Last request duration',unit:'seconds'};
  if(kind==='quantile')return {min:50,max:99,step:1,value:95,label:'Percentile to estimate',unit:'%'};
  return null;
}
function knob() { return target===4?Number($('knob').value):config(data.kind)?.value; }
function draw() {
  c.setTransform(2,0,0,2,0,0);c.clearRect(0,0,860,320);if(!data)return;
  const s=target,k=data.kind, n=nVisible(5);
  if(k==='sample') {
    text('A café queue',55,52,18,C.muted);box(55,76,280,157,'',C.orange);for(let i=0;i<4;i++)person(100+i*58,135);
    text('queue_depth',195,215,18,C.orange,'center');arrow(355,154,445,154);
    box(465,76,335,157,'',C.green);text(s>=2?'10:00':'timestamp?',490,120,24,s>=2?C.green:C.muted);text(s>=1?'4 people':'value?',490,160,24,s>=1?C.orange:C.muted);if(s>=3)text('ONE SAMPLE',490,207,14,C.green);
    caption('What was measured? How much? At what time?');calc(s>=2?'queue_depth · 10:00 · 4 people':'queue_depth = 4 people','A sample pairs one measured value with one timestamp. The metric name supplies its meaning.');
  } else if(['series','labels'].includes(k)) {
    text('queue_depth · people',80,35,17,C.orange);graph([2,4,6],['10:00','10:00:30','10:01'],{w:530,max:8,n:k==='series'?Math.min(3,n):3});
    if(k==='labels'&&s>=1)graph([1,3,5],null,{w:530,max:8,col:C.blue});
    card(662,90,155,k==='series'?'ONE SERIES':'instance = a',k==='series'?`${Math.min(3,n)} samples`:'2 → 4 → 6',C.orange);
    if(k==='labels') {box(662,203,155,48,'b: 1 → 3 → 5',C.blue,s>=1?1:.25);caption('Labels identify the series. Time orders its samples.');calc('2 identities × 3 timestamps = 2 series, 6 samples','Changing a label creates a different series. A later timestamp alone does not.');}
    else {caption('One queue, observed again and again');calc(`${Math.min(3,n)} dots = ${Math.min(3,n)} samples of the same series`,'The horizontal axis is time. The vertical axis is people waiting. A line helps your eye follow separate observations.');}
  } else if(['counter','gauge','reset','gauge_change'].includes(k)) {
    const vals=k==='counter'?[100,110,120,190]:k==='reset'?[100,115,5,20,35]:k==='gauge_change'?[6,5,3,4,2]:[2,4,1,3,2];
    text(k==='counter'||k==='reset'?'Requests served so far':'People waiting right now',80,35,17,C.orange);
    const pt=graph(vals,['0s','15s','30s','45s','60s'],{n:k==='reset'?Math.min(5,s===0?2:s<3?3:5):n,max:k==='reset'?140:undefined});
    if(k==='reset'&&s>=1){const [x,y]=pt(2);text('restart ↓',x+15,65,17,C.red);line(x,76,x,y-12,C.red);}
    const value=vals[Math.min(vals.length-1,k==='reset'?(s===0?1:s<3?2:4):n-1)];card(645,92,177,k==='counter'||k==='reset'?'COUNTER TOTAL':'CURRENT GAUGE',`${value}`,k==='reset'?C.red:C.orange,k==='counter'||k==='reset'?'requests':'people');
    if(k==='counter') {caption('New events add to the previous total');calc('100 → 110 means 10 more requests, not 110 more','Totals accumulate between scrapes. A counter decreases when it resets; ordinary new requests never subtract from it.');}
    else if(k==='reset') {caption('A falling counter needs reset handling');calc(s>=3?'+15 +5 +15 +15 = 50 observed events':'100 → 115 → 5 (restart)','Reset correction uses the new value after a decrease. It cannot recover unobserved activity just before the restart.');}
    else if(k==='gauge_change') {caption('The sign of a gauge change has meaning');calc('Observed endpoint change: 2 − 6 = −4 people','delta estimates change over the full window; deriv fits a per-second trend using the samples. Neither treats this drop as a counter restart.');}
    else {caption('A queue shrinking is ordinary behavior');calc('4 → 1 means the queue shrank by 3 people','A gauge measures current state. Its next value replaces the previous snapshot; it does not accumulate all arrivals.');}
  } else if(['observations','bucket_rule','buckets','hist_parts'].includes(k)) {
    const durations=[.12,.42,.8, ['buckets','hist_parts'].includes(k)?knob():1.4];
    if(k==='observations') {
      const count=Math.min(4,n);text('ONE DURATION PER FINISHED REQUEST',55,38,14,C.muted);
      durations.forEach((v,i)=>{const x=60+i*201;card(x,90,170,`Request ${i+1}`,`${v}s`,i<count?C.orange:C.muted);});caption('Four observations form a distribution');calc(s<3?`${count} observed request${count===1?'':'s'} · ${durations.slice(0,count).join('s, ')}s`:'0.12 + 0.42 + 0.80 + 1.40 = 2.74 seconds',s<3?'Each finished request contributes one measured duration. The unit is seconds.':'The mean is 2.74 ÷ 4 = 0.685s, but it hides the spread between fast and slow requests.');
    } else if(k==='bucket_rule') {
      text('THE RULE: duration ≤ 0.5 seconds',430,47,22,C.green,'center');
      durations.slice(0,3).forEach((v,i)=>{box(65,80+i*53,180,40,`${v}s`,C.orange,i<s?1:.3);if(i<s){arrow(260,100+i*53,410,100+i*53,v<=.5?C.green:C.red);text(v<=.5?'YES · increment':'NO · unchanged',440,106+i*53,18,v<=.5?C.green:C.red);}});
      const count=Math.min(2,s);card(659,103,148,'BUCKET VALUE',String(count),C.green,'observations');caption('A duration boundary is a test, not a stored duration');calc(`le="0.5" → ${count} observations so far`,'The boundary uses seconds. The bucket value counts how many observations satisfy the rule, including equality.');
    } else {
      const count=k==='buckets'?s:4, selected=durations.slice(0,count),counts=M.buckets(selected),sum=selected.reduce((a,b)=>a+b,0);
      text(k==='buckets'?(count?`Newest observation: ${fmt(durations[count-1])} seconds`:'Start: no requests observed'):'The same observations produce three kinds of totals',55,34,16,C.muted);
      counts.forEach((v,i)=>{const x=65+i*143,old=M.buckets(selected.slice(0,-1))[i],phase=k==='buckets'?Math.max(0,1-Math.abs(target-pos)):1,h=(old+(v-old)*phase)*34;c.fillStyle=i===3?C.green:C.blue;c.beginPath();c.roundRect(x,227-Math.max(3,h),90,Math.max(3,h),6);c.fill();text(String(v),x+45,211-h,23,C.ink,'center');text(['≤ 0.1s','≤ 0.5s','≤ 1s','+Inf'][i],x+45,252,16,C.muted,'center');});
      card(671,64,147,k==='buckets'?'OBSERVATIONS':'_count',String(count),C.green,'requests measured');card(671,180,147,k==='buckets'?'LATEST':'_sum',k==='buckets'?(count?`${fmt(durations[count-1])}s`:'—'):`${fmt(sum)}s`,C.orange,k==='buckets'?'one duration':'total duration');
      caption('One observation can increment several cumulative buckets');
      calc(k==='hist_parts'?`Mean = ${fmt(sum)}s ÷ ${count} = ${count?fmt(sum/count):0}s`:`Bucket counts: ${counts.join(', ')} · +Inf = ${count}`,k==='hist_parts'?'_sum adds durations; _count counts requests. _bucket preserves the distribution at each upper bound.':'A 0.42s request increments 0.5s, 1s, and +Inf. Never add these cumulative counts to obtain the total number of requests.');
    }
  } else if(['rate','rate_compare','increase'].includes(k)) {
    const r=M.rateExample(knob());text('Counter totals · requests',80,35,17,C.orange);graph(r.values,['0s','15s','30s','45s','60s'],{w:480,max:260});
    if(s>=1){line(80,266,560,266,C.green,3);text(`Broad change: +${r.change} in 60s`,320,286,16,C.green,'center');}
    if(s>=2&&k!=='rate'){line(440,248,560,248,C.purple,4);text(`+${knob()} / 15s`,690,250,16,C.purple,'center');}
    card(609,57,210,k==='rate'?'CHANGE · requests':'rate · requests/s',fmt(k==='rate'?r.change:r.rate),C.green);card(609,173,210,k==='rate'?'SPEED · requests/s':k==='increase'?'increase · requests':'irate · requests/s',k==='rate'&&s<3?'?':fmt(k==='rate'?r.rate:k==='increase'?r.increase:r.irate),C.purple);
    if(k==='rate')calc(s<3?`${r.values[4]} − 100 = ${r.change} requests in 60 seconds`:`${r.change} requests ÷ 60 seconds = ${fmt(r.rate)} requests/second`,'Divide the change in the total by elapsed seconds, not by the number of samples. Real rate() also handles resets and window boundaries; those come next.');
    else if(k==='increase')calc(`${fmt(r.rate)} requests/s × 75s = ${fmt(r.increase)} requests`,'The range is (−15s, 60s], but stored samples span 0s to 60s. Prometheus extrapolates to the window edges here; 112.5 is a valid estimate, not half a physical request.');
    else calc(`rate = ${r.change} / 60 = ${fmt(r.rate)}/s · irate = ${knob()} / 15 = ${fmt(r.irate)}/s`,'A 75s range ending at 60s includes all five samples. With these regular samples and no reset, the boundary extrapolation preserves this rate. irate uses only the final two samples.');
  } else if(['sum_time','average_time','extrema_time'].includes(k)) {
    const vals=[2,4,knob()],fn=target===4?$('function').value:k==='average_time'?'avg_over_time':k==='extrema_time'?'max_over_time':'sum_over_time',result=M.overTime(vals,fn);
    text('ONE SERIES · selected queue samples',60,40,16,C.muted);vals.forEach((v,i)=>card(62+i*194,76,162,['10:00','10:00:30','10:01'][i],`${v}`,C.orange,'people'));
    arrow(607,124,657,124);card(676,76,140,'RESULT',fmt(result),C.green,fn==='count_over_time'?'samples':'sample values');
    box(67,208,727,50,fn+'(queue_depth[90s])',C.green);caption('Same samples. Different questions.');
    const arithmetic={sum_over_time:`2 + 4 + ${knob()}`,avg_over_time:`(2 + 4 + ${knob()}) / 3`,min_over_time:`min(2, 4, ${knob()})`,max_over_time:`max(2, 4, ${knob()})`,count_over_time:'number of selected samples'};
    calc(`${fn}: ${arithmetic[fn]} = ${fmt(result)}`,fn==='sum_over_time'?'Adding queue snapshots does not count unique people or new arrivals. The same person may appear at several sample times.':fn==='avg_over_time'?'Each sample receives equal weight, even if the gaps between collected samples differ.':fn==='count_over_time'?'This counts collected samples. It does not count the events represented by a counter.':'The minimum and maximum describe observed samples. Changes between scrapes are not reconstructed.');
  } else if(k==='axes') {
    text('SERIES ↓',47,56,14,C.muted);text('TIME →',354,40,14,C.muted);['10:00','10:00:30','10:01'].forEach((v,i)=>text(v,257+i*150,76,15,C.muted,'center'));
    [[2,4,6],[1,3,5]].forEach((row,j)=>{text(`instance ${j?'b':'a'}`,48,129+j*69,16,j?C.blue:C.orange);row.forEach((v,i)=>box(210+i*150,96+j*69,95,48,String(v),i===2&&s>=1?C.green:j?C.blue:C.orange));if(s>=3)box(680,96+j*69,130,48,`Σ = ${j?9:12}`,C.purple);});
    if(s>=2){arrow(557,218,557,244);text('sum = 11',557,272,23,C.green,'center');}if(s>=3)text('sum_over_time →',713,67,14,C.purple,'center');
    calc('Across series: 6 + 5 = 11 · Across time: a = 12, b = 9','sum() combines selected series at one evaluation time. sum_over_time() produces one result per series from its history.');
  } else if(k==='aggregate') {
    text('INPUT: PER INSTANCE',60,35,15,C.muted);text('OUTPUT: PER SERVICE',607,35,15,C.muted);
    [2,4,3,5].forEach((v,i)=>{box(60,60+i*48,235,37,`${i<2?'api':'web'} / ${i%2?'b':'a'} = ${v}`,i<2?C.orange:C.blue);if(s>=2+(i>=2?1:0))arrow(310,79+i*48,606,i<2?110:203,i<2?C.orange:C.blue);});
    box(340,113,203,49,'sum by(service)',C.green);card(624,58,180,'api',s>=2?'2 + 4 = 6':'?',C.orange);card(624,169,180,'web',s>=3?'3 + 5 = 8':'?',C.blue);caption('Keep service. Remove the instance distinction.');calc('api → 6 · web → 8','by(service) keeps the grouping label. without(instance) drops that label but preserves other dimensions that might still be present.');
  } else if(k==='ratio') {
    text('100 requests per second',65,42,19,C.blue);for(let i=0;i<100;i++)dot(75+(i%20)*24,75+Math.floor(i/20)*31,7,s>=1&&i<8?C.red:C.blue);
    card(614,80,204,'ERROR FRACTION',s>=3?'8%':'8 / 100',C.red);text('8 errors per second',65,250,19,C.red);caption('Same population · same time window · compatible labels');calc('8 errors/s ÷ 100 requests/s = 0.08 = 8%','The time units cancel. Combine error rates and total rates before division; averaging instance percentages can weight tiny and busy instances incorrectly.');
  } else if(['matching','group_left'].includes(k)) {
    const many=k==='group_left',names=many?['api / a','api / b','web / a','web / b']:['api','web'];text('MEASUREMENTS',63,35,14,C.muted);text('ONE MATCH PER SERVICE',571,35,14,C.muted);
    names.forEach((name,i)=>{const group=many?Math.floor(i/2):i,y=many?56+i*51:72+i*114;box(59,y,200,40,name,group?C.blue:C.orange);if(s>=2+group)arrow(272,y+20,559,group?214:100,group?C.blue:C.orange);});
    box(577,74,236,52,'api → team: platform',C.orange);box(577,188,236,52,'web → team: experience',C.blue);if(s>=1)box(340,121,151,43,'on(service)',C.green);caption('Match identities, never display order');calc(many?'Many measurements × one metadata match':'api pairs with api · web pairs with web',many?'group_left(team) permits this many-to-one match and copies team. An unmatched measurement disappears; duplicate right-side service keys cause an error.':'Arithmetic pairs series by the selected label key. Unmatched series do not automatically produce a zero result.');
  } else if(['vectors','window','offset'].includes(k)) {
    const vals=[2,5,3,6,4,7,5],labels=['−6m','−5m','−4m','−3m','−2m','−1m','now'];graph(vals,labels,{w:700,max:9,col:C.blue});
    if(k==='vectors') {
      if(s>=2){c.fillStyle='#84e7c422';c.fillRect(196,53,585,185);}line(780,50,780,237,C.orange,3);text('Evaluation time',780,36,16,C.orange,'right');
      caption(s<2?'Instant: one selected value per series':'Range vector: each series keeps its selected history');calc(s<2?'queue_depth → one value per matching series':'queue_depth[5m] → separate sample windows','A range query repeats evaluations to build a chart. A range vector is a value type inside an expression; the two are different.');
    } else {
      const left=k==='offset'?(s>=1?1:3):(s===4?3:2),right=left+3,x=80+left*700/6,xx=80+right*700/6;c.fillStyle='#84e7c420';c.fillRect(x,52,xx-x,186);line(x,48,x,240,C.red);line(xx,48,xx,240,C.green);text('(',x,47,29,C.red,'center');text(']',xx,47,29,C.green,'center');
      caption(k==='offset'?'Both boundaries move together':'Left boundary excluded · right boundary included');calc(k==='offset'?'[3m] offset 2m → the whole window shifts 2 minutes back':'range = (evaluation time − duration, evaluation time]','Dots are collected observations. Only samples inside the selected window contribute. A gap in history is missing evidence, not proof of zero.');
    }
  } else if(k==='filter') {
    ['api / a = 1','web / a = 1','api / b = 0','web / b = 1'].forEach((name,i)=>{const yes=i%2===0;box(47,50+i*52,235,39,name,yes?C.orange:C.blue,s>=2&&!yes?.3:1);if(s>=3&&yes){arrow(293,70+i*52,601,70+i*52);box(615,50+i*52,205,39,name,C.green);}});box(327,107,235,59,'service="api"',C.green);caption('Keep matching labels, including the API value of zero');calc('up{service="api"} → both API instances','The service label is a string used to select series. Filtering by service does not filter out a zero numeric value.');
  } else if(k==='missing') {
    card(43,73,240,'SCRAPE SUCCEEDED','up = 1',C.green);card(310,73,240,'SCRAPE FAILED','up = 0',s>=1?C.red:C.muted);card(577,73,240,'NO USABLE SERIES','absent',s>=2?C.purple:C.muted);
    if(s>=3)box(112,217,636,48,'Expected target inventory − observed targets',C.orange);caption('Three observations with different meanings');calc('No sample ≠ a sample whose value is 0','absent() detects an empty selection. To identify which expected targets vanished, compare with an inventory containing those identities.');
  } else if(k==='quantile') {
    const q=knob()/100,r=M.quantile(q),counts=[20,60,90,100,100],bounds=['0.1s','0.5s','1s','2s','+Inf'];text('CUMULATIVE COUNTS · 100 observations',60,34,14,C.muted);
    counts.forEach((v,i)=>{const x=66+i*147,h=v*1.65;c.fillStyle=i===r.index&&s>=2?C.orange:C.blue;c.fillRect(x,239-h,85,h);text(String(v),x+42,226-h,18,C.ink,'center');text(bounds[i],x+42,264,16,C.muted,'center');});
    if(s>=1){line(48,239-r.rank*1.65,817,239-r.rank*1.65,C.green,2);text(`rank ${r.rank}`,818,229-r.rank*1.65,14,C.green,'right');}
    calc(`p${knob()} ≈ ${fmt(r.lower)} + (${r.rank} − ${r.before}) / (${r.after} − ${r.before}) × (${r.upper} − ${r.lower}) = ${fmt(r.value)}s`,'For classic histograms, this example interpolates within the containing finite bucket. Bucket boundaries limit precision; the raw request duration is not recovered.');
  } else if(k==='hist_pipeline') {
    pipeline(['Instance|buckets','rate|each series','sum by|service, le','histogram_|quantile','Service|p95']);caption('Keep le until the quantile calculation');calc('histogram_quantile(0.95, sum by(service, le)(rate(…_bucket[5m])))','First handle resets per original counter, then combine matching boundaries. Do not average instance p95 values or discard the le label early.');
  } else if(k==='representations') {
    card(38,73,248,'CLASSIC HISTOGRAM','bucket series',C.blue,'le + _count + _sum');card(307,73,248,'NATIVE HISTOGRAM','structured sample',s>=1?C.green:C.muted,'distribution in one sample');card(576,73,248,'SUMMARY','precomputed quantile',s>=2?C.orange:C.muted,'when configured to expose it');
    if(s>=3)box(139,216,580,50,'Quantiles cannot generally be averaged together',C.red);calc('Histogram evidence can combine; summary quantiles generally cannot','The runnable fixtures use classic histogram series. Native histograms use different storage and query forms; do not paste classic syntax blindly.');
  } else if(k==='pipeline') {
    pipeline(['Raw|gauges','sum|instances','Evaluate|every 1m','avg_over_time|derived values','Record|for reuse']);caption('Inner expression → repeated evaluation → outer calculation');calc('avg_over_time((sum(queue_depth))[30m:1m])','The subquery creates a time grid of calculated values. A recording rule instead stores recurring calculations for reuse; both require explicit timing and label choices.');
  } else if(k==='alert') {
    ['Healthy: up=1','Failed: up=0','Missing: no series'].forEach((name,i)=>box(34+i*277,42,239,48,name,[C.green,C.red,C.purple][i],s>=1?1:.6));
    text('WHEN THE CHOSEN CONDITION STAYS ACTIVE',430,135,14,C.muted,'center');box(87,163,228,61,'Pending',C.orange,s>=2?1:.25);arrow(331,194,533,194,s>=3?C.green:C.line);text('for: 5m',430,179,17,C.green,'center');box(551,163,228,61,'Firing',C.red,s>=4?1:.25);caption('A hold timer is separate from a query lookback');calc('Query: what evidence? · for: how long continuously active?','A five-minute range in a query does not itself keep an alert pending for five minutes. The alert rule’s for duration controls that hold timer.');
  } else if(k==='cardinality') {
    const vals=['2 services','× 2 instances','× 3 statuses','× request IDs','Unbounded growth'];pipeline(vals.map(v=>v.replace(' ','|')));caption('Each distinct label combination identifies another series');calc(s<3?'2 × 2 × 3 = up to 12 label combinations':'2 × 2 × 3 × unbounded request IDs → unbounded potential series','Actual series depend on which combinations occur. Bounded labels help control cost; unique request IDs usually belong in logs or traces.');
  } else if(k==='incident') {
    const names=['TRAFFIC','ERROR FRACTION','P95 LATENCY','FAILED TARGETS'],values=s===0?['34 /s','1%','0.44s','0']:['102 /s','8%','0.88s','1'];
    names.forEach((name,i)=>card(28+i*211,84,188,name,values[i],i===0?C.blue:s?C.red:C.green));caption(s?'Symptoms are evidence; root cause still needs investigation':'Begin with a normal baseline');calc('Traffic + error fraction + tail latency + availability','Check aligned populations and time windows. More errors can reflect more traffic; a higher error fraction tells a different story. These illustrative signals do not establish causation.');
  } else if(['budget','burn'].includes(k)) {
    card(44,77,234,'SUCCESS OBJECTIVE','99.9%',C.blue);card(313,77,234,'ALLOWED BAD FRACTION','0.001',C.green,'0.1%');card(582,77,234,k==='budget'?'GOOD EVENTS / TOTAL':'OBSERVED BAD FRACTION',k==='budget'?'≥ 0.999':'0.01',C.orange,k==='budget'?'over the reporting period':'1% in the chosen window');
    if(s>=2)box(139,218,582,48,k==='budget'?'1 − 0.999 = 0.001':'0.01 ÷ 0.001 = 10× burn',C.green);caption('Keep fractions, percentages, and time periods distinct');calc(k==='budget'?'Allowed bad fraction = 1 − target success fraction':'Burn rate = observed bad fraction / allowed bad fraction = 10',k==='budget'?'Specify which events count, what “good” means, and the reporting period. A short measurement window is not the complete SLO reporting period.':'Ten means ten times the sustainable bad-event fraction. It is not ten minutes remaining, and it does not alone tell you the remaining monthly budget.');
  } else {text('This lesson illustration is unavailable.',60,130,20,C.red);calc('Use the written lesson below.','The curriculum and renderer must use a supported concept kind.');}
}
function update() {
  if(!data)return;const step=data.steps[target];$('step').value=target;$('counter').textContent=`MOMENT ${target+1} OF ${data.steps.length}`;$('step-title').textContent=step.title;$('narration').textContent=step.explanation;
  $('play').textContent=playing?'Ⅱ Pause':'▶ Play story';$('play').setAttribute('aria-label',playing?'Pause story':'Play story');$('back').disabled=target===0;$('next').disabled=target===4;
  $('canvas').setAttribute('aria-label',`${data.title}. ${step.title}. ${step.explanation}`);
  const cfg=config(data.kind);$('explore').hidden=!(cfg&&target===4);$('function-row').hidden=!['sum_time','average_time','extrema_time'].includes(data.kind);if(cfg)$('knob-value').textContent=`${fmt(Number($('knob').value))} ${cfg.unit}`;
  draw();height();
}
function advance(value) {playing=false;target=Math.max(0,Math.min(4,value));elapsed=0;update();}
$('play').onclick=()=>{if(!data)return;playing=!playing;if(playing&&target===4){target=0;pos=0;}elapsed=0;update();};$('back').onclick=()=>advance(target-1);$('next').onclick=()=>advance(target+1);$('step').oninput=e=>advance(Number(e.target.value));$('knob').oninput=update;$('function').onchange=update;
window.addEventListener('message',e=>{
  if(e.source!==window.parent||e.data?.type!=='streamlit:render')return;
  data=e.data.args.animation;
  if(seenLesson!==e.data.args.level){seenLesson=e.data.args.level;pos=0;target=0;playing=false;elapsed=0;const cfg=config(data.kind);if(cfg){for(const key of ['min','max','step','value'])$('knob')[key]=cfg[key];$('knob-label').textContent=cfg.label;}$('function').value=data.kind==='average_time'?'avg_over_time':data.kind==='extrema_time'?'max_over_time':'sum_over_time';}
  $('title').textContent=data.title;update();
});
let heightFrame=0;
new ResizeObserver(()=>{cancelAnimationFrame(heightFrame);heightFrame=requestAnimationFrame(height);}).observe(document.querySelector('.shell'));
function frame(t){const dt=Math.min(100,t-last||16);last=t;const before=pos;pos=reduced.matches?target:pos+(target-pos)*Math.min(1,dt/130);if(Math.abs(pos-target)<.005)pos=target;if(playing){elapsed+=dt*Number($('speed').value);if(elapsed>=8000){elapsed=0;if(target<4)target++;else playing=false;update();}}if(pos!==before)draw();requestAnimationFrame(frame);}
post('streamlit:componentReady',{apiVersion:1});height();requestAnimationFrame(frame);

window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;if(e.key==='ArrowRight'){e.preventDefault();advance(target+1);}if(e.key==='ArrowLeft'){e.preventDefault();advance(target-1);}if(e.code==='Space'){e.preventDefault();$('play').click();}});
