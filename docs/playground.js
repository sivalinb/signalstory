'use strict';
const el=id=>document.getElementById(id);
let course,current,frame;
const text=(id,value)=>{el(id).textContent=value||'';};
const allConcepts=()=>course.missions.flatMap(m=>m.concepts);
const option=(value,label)=>{const n=document.createElement('option');n.value=value;n.textContent=label;return n;};
function renderConcept(){
  const m=course.missions.find(m=>m.id===el('mission').value);
  current=m.concepts.find(c=>c.id===el('concept').value);
  text('objective',m.objective);text('question',current.check.prompt);text('feedback','');
  el('answers').replaceChildren();current.check.options.forEach((answer,i)=>{const label=document.createElement('label');label.className='choice';const input=document.createElement('input');input.type='radio';input.name='prediction';input.value=String(i);label.append(input,document.createTextNode(answer));el('answers').append(label);});
  text('concept-title',current.title);for(const field of ['explanation','analogy','example','remember'])text(field,current[field]);text('sql',current.sql_connection);
  el('written').replaceChildren();const steps=current.animation.steps||current.animation.frames;steps.forEach((s,i)=>{const h=document.createElement('h4');h.textContent=`${i+1}. ${s.title||"Moment "+(i+1)}`;const p=document.createElement('p');p.textContent=(s.explanation||s.narration||'')+(s.nodes?' '+s.nodes.map(n=>n.label+': '+n.value).join('. '):'');el('written').append(h,p);});
  el('sources').replaceChildren();current.sources.forEach(source=>{const url=typeof source==='string'?source:source.url;const a=document.createElement('a');a.href=url;a.textContent=typeof source==='string'?'Read the original reference ↗':source.title+' ↗';a.target='_blank';a.rel='noopener noreferrer';el('sources').append(a);});
  el('animation-host').replaceChildren();frame=document.createElement('iframe');frame.title=current.title+' interactive animation';frame.src='playground/'+(current.renderer==='promql'?'concept':'scene')+'/index.html';el('animation-host').append(frame);
  try{el('note').value=localStorage.getItem('signalstory-note-'+current.id)||'';}catch{el('note').value='';}text('note-feedback','');
  const hash=new URLSearchParams({lesson:current.id});history.replaceState(null,'','#'+hash);
  const index=allConcepts().findIndex(c=>c.id===current.id);el('previous').disabled=index===0;el('next').disabled=index===allConcepts().length-1;
}
function selectMission(conceptId){const m=course.missions.find(m=>m.id===el('mission').value);el('concept').replaceChildren(...m.concepts.map(c=>option(c.id,c.title)));if(conceptId)el('concept').value=conceptId;renderConcept();}
function move(amount){const all=allConcepts(),index=all.findIndex(c=>c.id===current.id),next=all[index+amount];if(!next)return;el('mission').value=course.missions.find(m=>m.concepts.some(c=>c.id===next.id)).id;selectMission(next.id);el('studio').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
window.addEventListener('message',event=>{const frames=[el('hero-frame'),frame];const source=frames.find(f=>f&&f.contentWindow===event.source);if(!source||event.origin!==location.origin)return;if(event.data.type==='streamlit:componentReady'){source.contentWindow.postMessage({type:'streamlit:render',args:source===frame?{animation:current.animation,title:current.title,level:current.id}:{},disabled:false,theme:{base:'light'}},location.origin);}if(event.data.type==='streamlit:setFrameHeight'&&Number.isFinite(event.data.height))source.style.height=Math.max(0,Math.min(event.data.height,1800))+'px';});
el('prediction-form').addEventListener('submit',event=>{event.preventDefault();const chosen=document.querySelector('input[name=prediction]:checked');if(!chosen){text('feedback','Choose the answer you think is most likely.');return;}text('feedback',(Number(chosen.value)===current.check.answer?'You predicted it. ':'A useful discovery. ')+current.check.explanation);});
el('save-note').addEventListener('click',()=>{try{localStorage.setItem('signalstory-note-'+current.id,el('note').value);text('note-feedback','Saved only in this browser.');}catch{text('note-feedback','Browser storage is unavailable. Copy your explanation somewhere private.');}});
el('share').addEventListener('click',async()=>{try{const url=new URL(location.href);url.hash=new URLSearchParams({lesson:current.id});await navigator.clipboard.writeText(url.href);el('share').textContent='Lesson link copied ✓';setTimeout(()=>el('share').textContent='Copy lesson link',2000);}catch{el('share').textContent='Copy the address from your browser';}});
el('previous').addEventListener('click',()=>move(-1));el('next').addEventListener('click',()=>move(1));
el('mission').addEventListener('change',()=>selectMission());el('concept').addEventListener('change',renderConcept);
fetch('playground/course.json').then(response=>{if(!response.ok)throw Error('Course unavailable');return response.json();}).then(data=>{course=data;el('mission').replaceChildren(...course.missions.map((m,i)=>option(m.id,`${String(i+1).padStart(2,'0')} · ${m.title}`)));const id=new URLSearchParams(location.hash.slice(1)).get('lesson');const requested=course.missions.find(m=>m.concepts.some(c=>c.id===id));if(requested)el('mission').value=requested.id;selectMission(requested?id:undefined);}).catch(()=>text('objective','The course could not load. Refresh the page or run the Python studio.'));
