'use strict';
const $ = id => document.getElementById(id);
const fmt = n => typeof n === 'number' ? new Intl.NumberFormat('en-GB',{maximumFractionDigits:3}).format(n) : '—';
let requestVersion=0;
let catalog;

/** Fetch JSON from the local read-only API and propagate visible operational errors. */
async function api(path,params={}){
  const response=await fetch(path+'?'+new URLSearchParams(params));
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||'Unable to read this series');
  return data;
}
/** Replace table content with text-only cells; source text is never interpreted as HTML. */
function table(id,rows){
  $(id).replaceChildren(...rows.map(values=>{
    const tr=document.createElement('tr');
    values.forEach(value=>{const td=document.createElement('td');td.textContent=String(value??'—');tr.append(td);});
    return tr;
  }));
}
/** Render calendar-spaced observed values, keeping nulls and absent periods as line breaks. */
function draw(rows,unit){
  const svg=$('chart');svg.replaceChildren();
  const valid=rows.filter(r=>r.value!==null);if(!valid.length)return;
  const namespace='http://www.w3.org/2000/svg';
  const node=(tag,attrs,text)=>{const el=document.createElementNS(namespace,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));if(text!==undefined)el.textContent=text;svg.append(el);return el;};
  const number=p=>p.includes('Q')?Number(p.slice(0,4))*4+Number(p.at(-1))-1:Number(p.slice(0,4))*12+Number(p.slice(-2))-1;
  const start=Math.min(...rows.map(r=>number(r.period))),end=Math.max(...rows.map(r=>number(r.period)));
  let low=Math.min(...valid.map(r=>r.value)),high=Math.max(...valid.map(r=>r.value));
  const pad=(high-low)*.15||.5;low-=pad;high+=pad;
  const x=r=>60+(number(r.period)-start)/Math.max(1,end-start)*710;
  const y=v=>210-(v-low)/(high-low)*180;
  for(let i=0;i<4;i++){const v=low+(high-low)*i/3;node('line',{x1:60,x2:770,y1:y(v),y2:y(v),stroke:'#c7cbc4','stroke-width':.7});node('text',{x:50,y:y(v)+4,'text-anchor':'end',fill:'#52636a','font-size':11},fmt(v));}
  let segment=[],previous=null;
  const flush=()=>{if(segment.length)node('polyline',{points:segment.join(' '),fill:'none',stroke:'#31594b','stroke-width':2.5});segment=[];};
  rows.forEach(r=>{const n=number(r.period);if(r.value===null){flush();previous=null;return;}if(previous!==null&&n!==previous+1)flush();segment.push(x(r)+','+y(r.value));previous=n;node('circle',{cx:x(r),cy:y(r.value),r:2.5,fill:'#31594b'});});flush();
  node('text',{x:60,y:243,fill:'#52636a','font-size':11},rows[0].period);node('text',{x:770,y:243,'text-anchor':'end',fill:'#52636a','font-size':11},rows.at(-1).period);
  svg.setAttribute('aria-label',valid.length+' observations; '+unit+'; data table below');
}
/** Clear all previous-series content before showing an unavailable state. */
function clearReport(){
  for(const id of ['value','period','change','signal'])$(id).textContent='—';
  for(const id of ['unit','freshness','change-unit','signal-detail','definition','forecast-note','revision-note'])$(id).textContent='No selected observations';
  for(const id of ['forecast','revisions','observations','peers'])table(id,[]);
  $('source').replaceChildren();$('source-link').hidden=true;$('hash').textContent='No source selected';$('chart').replaceChildren();
}
/** Load a selected country/indicator/vintage, ignoring responses superseded by a newer filter. */
async function load(){
  const version=++requestVersion;
  const params={country:$('country').value,indicator:$('indicator').value,mode:$('mode').value};
  if($('vintage').value)params.run_id=$('vintage').value;
  try{
    const report=await api('/api/report',params);if(version!==requestVersion)return;
    clearReport();
    const selected=$('vintage').value;
    $('vintage').replaceChildren(new Option('Latest successful',''),...(report.vintages||[]).map(n=>new Option('Vintage '+n,String(n))));
    $('vintage').value=selected;
    $('notice').className='notice';
    const summary=report.summary;
    if(!summary.available){$('notice').textContent='No collected series for this selection. Collect an explicit slice or select an available demo country.';return;}
    $('notice').textContent=(params.mode==='demo'?'ILLUSTRATIVE DEMO — authored data, not official economic values.':'COLLECTED OFFICIAL DATA — source and vintage shown below.')+(report.shared_context?' EURUSD is shared currency context; country selection does not make it a national series.':'');
    $('value').textContent=fmt(summary.value);$('unit').textContent=summary.unit;$('period').textContent=summary.period;
    $('freshness').textContent=(summary.stale?'Older than project freshness threshold':'Within project freshness threshold')+' · '+summary.age_days+' days after period end';
    $('change').textContent=fmt(summary.change);$('change-unit').textContent=summary.change_unit;
    const signal=report.anomaly;$('signal').textContent=signal.available?(signal.flagged?'Investigate':'No flag'):'Unavailable';
    $('signal-detail').textContent=signal.available?((signal.rule==='flat_baseline_shift'?'Flat reference comparison':'Previous '+signal.window+' periods')+' · z='+fmt(signal.z_score)):signal.reason;
    $('definition').textContent=report.catalogue.definition+' '+report.rows.length+' returned periods; '+summary.missing+' explicit missing cells.';
    $('chart-unit').textContent=summary.unit.toUpperCase();draw(report.rows,summary.unit);
    const evidence=[['Provider',params.mode==='demo'?'Authored demo':report.catalogue.provider],['Series',report.catalogue.dataset],['Frequency',report.catalogue.frequency],['Entity',report.country],['Retrieved',report.retrieved_at],['Vintage',report.run_id],['Source flags',summary.status||'None supplied']];
    evidence.forEach(([key,value])=>{const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=String(value);$('source').append(dt,dd);});
    $('hash').textContent=report.sha256;
    if(report.url.startsWith('https://')){$('source-link').href=report.url;$('source-link').hidden=false;}
    const forecast=report.forecast;
    $('forecast-note').textContent=forecast.available?forecast.origins.length+' expanding origins · selected '+forecast.selected+' · next-period baseline '+fmt(forecast.estimate)+' '+summary.unit:forecast.reason;
    if(forecast.available)table('forecast',Object.entries(forecast.models).map(([name,m])=>[name,fmt(m.mae),fmt(m.rmse)]));
    $('revision-note').textContent=report.vintages.length<2?'Collect this series again to compare vintages.':report.revisions.length+' changed cells vs previous collected slice. Different request windows may add/remove periods.';
    table('revisions',report.revisions.map(r=>[r.period+' / '+r.kind,fmt(r.old_value)+' ['+(r.old_status||'')+']',fmt(r.new_value)+' ['+(r.new_status||'')+']']));
    table('observations',report.rows.map(r=>[r.period,fmt(r.value),r.status||'No flag supplied']));
    $('peer-note').textContent='Choose a peer to compare at a shared nonmissing period.';
  }catch(error){if(version!==requestVersion)return;clearReport();$('notice').className='notice error';$('notice').textContent=error.message;}
}
/** Compare only the current country and an explicit distinct peer. */
async function peers(event){
  event.preventDefault();const version=requestVersion;
  try{const result=await api('/api/compare',{countries:[$('country').value,$('peer').value].join(','),indicator:$('indicator').value,mode:$('mode').value});if(version!==requestVersion)return;
    $('peer-note').textContent=result.available?'Shared observation period: '+result.period+' · '+result.unit:result.reason;
    table('peers',result.available?result.peers.map(r=>[r.name,fmt(r.value),r.run_id+' / '+r.retrieved_at]):[]);
  }catch(error){$('peer-note').textContent=error.message;table('peers',[]);}
}
/** Calculate a user-entered mechanical scenario independently of the selected country series. */
async function scenario(event){
  if(event)event.preventDefault();
  try{const result=await api('/api/scenario',Object.fromEntries(['imports','fx','shock','debt','bps'].map(id=>[id,$(id).value])));
    $('scenario-result').replaceChildren();
    for(const [label,value] of [['Invoice change / EUR',result.invoice_delta_eur],['Annual interest change / EUR',result.annual_interest_delta_eur]]){const div=document.createElement('div'),strong=document.createElement('strong');strong.textContent=fmt(value);div.append(strong,document.createTextNode(label));$('scenario-result').append(div);}
  }catch(error){$('scenario-result').textContent=error.message;}
}
/** Initialize controls once; subsequent changes call the same server-side calculations. */
async function init(){
  try{catalog=await api('/api/catalog');
    for(const [code,name] of Object.entries(catalog.countries)){$('country').add(new Option(name,code));$('peer').add(new Option(name,code));}
    for(const [code,spec] of Object.entries(catalog.indicators))$('indicator').add(new Option(spec.title,code));
    $('country').value='DE';$('peer').value='FR';$('mode').value=catalog.default_mode;
    $('filters').addEventListener('submit',event=>{event.preventDefault();load();});
    for(const id of ['country','indicator','mode'])$(id).addEventListener('change',()=>{$('vintage').value='';load();});
    $('vintage').addEventListener('change',load);$('peer-form').addEventListener('submit',peers);$('scenario-form').addEventListener('submit',scenario);
    await Promise.all([load(),scenario()]);
  }catch(error){$('notice').textContent=error.message;$('notice').className='notice error';}
}
init();
