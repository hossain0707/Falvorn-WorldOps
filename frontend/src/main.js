import {api, post, setApiKey} from './api.js';
import {renderMap, escapeText as esc, initials, colorAt, timeAgo} from './render.js';
const $ = id => document.getElementById(id);
const S = {worlds:[], world:null, agents:[], events:[], metrics:null, approvals:[], landmarks:null, busy:false};
let refreshTimer = null;
const icons = {world_created:'◇',world_started:'▶',world_paused:'Ⅱ',agent_joined:'+',move:'↗',rest:'◷',work:'⬡',talk:'☰',reflect:'✧',proposal:'⚖',vote:'✓',blocked_action:'⛨',approval_requested:'◇',approval_granted:'✓',approval_rejected:'×',external_feed:'↧',model_fallback:'!',dispatch_failed:'!',external_dispatched:'⇧'};
function toast(msg) { const t=$('toast'); t.textContent=String(msg); t.classList.add('visible'); clearTimeout(t._t); t._t=setTimeout(()=>t.classList.remove('visible'),4000); }
function connection(yes) { $('connection').className='connection ' + (yes?'online':'offline'); $('connection').innerHTML=`<i></i>${yes?'CONNECTED':'DISCONNECTED'}`; }
async function refresh() {
  if (S.busy) return; S.busy=true;
  try {
    const worlds=await api('/worlds'); S.worlds=worlds;
    if (!S.world || !worlds.some(w=>w.id===S.world.id)) S.world=worlds[0]||null;
    else S.world=worlds.find(w=>w.id===S.world.id);
    if(S.world) {
      const w=S.world.id;
      const [agents,events,metrics,approvals,meta]=await Promise.all([
        api(`/worlds/${w}/agents`),api(`/worlds/${w}/events?limit=65`),
        api(`/worlds/${w}/metrics`),api(`/worlds/${w}/approvals`),api('/meta')]);
      Object.assign(S,{agents,events,metrics,approvals,landmarks:meta.landmarks});
    } else Object.assign(S,{agents:[],events:[],metrics:null,approvals:[],landmarks:null});
    connection(true); render();
  } catch(err) { connection(false); if(!String(err.message).includes('Failed to fetch'))toast('Connection: '+err.message); }
  finally { S.busy=false; }
}
function render() {
  const w=S.world, m=S.metrics;
  $('world-list').innerHTML='';
  for (const world of S.worlds) {
    const b=document.createElement('button');b.className='world-entry'+(w?.id===world.id?' current':'');
    b.innerHTML=`<span>◈</span> <span>${esc(world.name)}</span><span>${world.status==='running'?'●':''}</span>`;
    b.onclick=()=>{S.world=world;refresh();}; $('world-list').appendChild(b);
  }
  $('world-title').textContent=w?.name||'No active world';
  $('world-subtitle').textContent=w?`${w.scenario.toUpperCase()} EXPERIMENT • SEED ${w.seed}`:'Create a world to get started';
  $('world-badge').textContent=w?.status?.toUpperCase()||'OFFLINE';
  $('world-badge').className='status-badge '+(w?.status==='running'?'running':'');
  $('toggle-running').disabled=!w;
  $('toggle-running').textContent=w?.status==='running'?'Ⅱ Pause simulation':'▶ Start simulation';
  $('step-one').disabled=$('step-ten').disabled=!w;
  $('metric-agents').textContent=m?.agents??'—';
  $('metric-turns').textContent=m?.turn?.toLocaleString()??'—';
  $('metric-energy').textContent=m?`${m.average_energy}%`:'—';
  $('metric-blocks').textContent=m?.safety_blocks??'—';
  $('map-foot').textContent=w?`${w.name.toUpperCase()} • TURN ${w.turn}`:'WORLD STATE IDLE';
  renderMap($('world-svg'),S.agents,S.landmarks||undefined,showAgent);
  $('agent-count').textContent=S.agents.length;
  $('agents').innerHTML='';
  if(!S.agents.length) $('agents').innerHTML='<p class="muted">Create a world to populate agents.</p>';
  S.agents.forEach((a,i)=>{
    const b=document.createElement('button'); b.className='agent-item';
    b.innerHTML=`<span class="agent-avatar" style="background:${colorAt(i)}">${esc(initials(a.name))}</span>
      <span style="min-width:0"><span class="agent-name">${esc(a.name)}</span><span class="agent-role" style="display:block">${esc(a.role)}</span></span>
      <span class="agent-side">${a.energy}%<span class="agent-role" style="display:block">${esc(a.location)}</span></span>`;
    b.onclick=()=>showAgent(a.id);$('agents').appendChild(b);
  });
  $('feed').innerHTML='';
  if(!S.events.length) $('feed').innerHTML='<div class="empty-feed">Events will appear here as agents act.</div>';
  S.events.forEach(e=>{
    const entry=document.createElement('article');entry.className='activity-entry';
    entry.innerHTML=`<div class="event-icon ${esc(e.kind)}">${icons[e.kind]||'◈'}</div>
      <div class="event-body"><div class="event-kind">${esc(e.kind.replaceAll('_',' '))} <span style="font-size:10px;color:#637c96;font-weight:400">#${e.turn}</span></div>
      <div class="event-message"></div></div><div class="event-time">${esc(timeAgo(e.created_at))}</div>`;
    entry.querySelector('.event-message').textContent=e.message;
    $('feed').appendChild(entry);
  });
  const pending=S.approvals.filter(a=>a.status==='pending');
  $('approval-count').textContent=pending.length;
  $('approvals').innerHTML='';
  if(!S.approvals.length) $('approvals').innerHTML='<p class="muted">No external actions requested. Autonomous dispatch is disabled.</p>';
  S.approvals.slice(0,12).forEach(a=>{
    const box=document.createElement('div'); box.className='approval-item';
    box.innerHTML=`<div class="approval-title">${esc(a.action_type.replaceAll('_',' '))} <b>${esc(a.status.toUpperCase())}</b></div><div class="approval-content"></div><div class="approval-buttons"></div>`;
    box.querySelector('.approval-content').textContent=a.payload?.summary||'External action request';
    const buttons=box.querySelector('.approval-buttons');
    if(a.status==='pending') {
      addButton(buttons,'Approve','approve',()=>review(a.id,'approve'));
      addButton(buttons,'Reject','',()=>review(a.id,'reject'));
    } else if(a.status==='approved') addButton(buttons,'Dispatch (gateway)','approve',()=>dispatch(a.id));
    $('approvals').appendChild(box);
  });
}
function addButton(root,label,className,click) {let b=document.createElement('button');b.textContent=label;b.className=className;b.onclick=click;root.appendChild(b);}
function modal(title,fields,callback,submit='Confirm') {
  const form=$('dialog-form');$('dialog-title').textContent=title;$('dialog-submit').textContent=submit;
  $('dialog-fields').innerHTML=fields;
  form.onsubmit=async e=>{
    if(e.submitter?.value==='cancel')return;
    e.preventDefault();
    const data=new FormData(form);
    $('dialog-submit').disabled=true;
    try {await callback(data); $('dialog').close(); await refresh();}
    catch(err){toast(err.message);}
    finally{$('dialog-submit').disabled=false;}
  };
  $('dialog').showModal();
}
function createWorld() {modal('Create a new world',`
  <label class="dialog-label" for="world-name">World name</label><input class="dialog-field" id="world-name" name="name" required minlength="3" maxlength="100" placeholder="e.g. Horizon Research Lab" />
  <label class="dialog-label" for="world-scenario">Scenario</label><select class="dialog-field" id="world-scenario" name="scenario"><option value="town">Autonomous town / research</option><option value="workplace">Business operations / human approvals</option></select>
  <label class="dialog-label" for="world-seed">Reproducibility seed</label><input class="dialog-field" type="number" id="world-seed" name="seed" min="0" max="2147483647" value="42" />
  <label class="checkbox-line"><input type="checkbox" name="starter_agents" checked /> Populate eight original test agents</label>`,async data=>{
    const w=await post('/worlds',{name:data.get('name'),scenario:data.get('scenario'),seed:Number(data.get('seed')),starter_agents:data.get('starter_agents')==='on'});
    S.world=w;toast('World created successfully');
  },'Create world'); }
async function toggleWorld() {if(!S.world)return;await post(`/worlds/${S.world.id}/${S.world.status==='running'?'pause':'start'}`);await refresh();}
async function step(count) {if(!S.world)return;const result=await post(`/worlds/${S.world.id}/steps`,{count});toast(`${result.steps.length} turn(s) completed`);await refresh();}
function feedModal() {if(!S.world)return toast('Create a world first');modal('Inject untrusted information',`
  <p class="dialog-help">The content is labeled untrusted. It will be logged for agent observation, not treated as instructions.</p>
  <label class="dialog-label">Source label</label><input class="dialog-field" name="source" value="external-test-feed" required maxlength="80" />
  <label class="dialog-label">Event content</label><textarea class="dialog-field" name="content" required maxlength="1000" rows="4" placeholder="Insert a news claim or red-team test message..."></textarea>`, async data=>{await post(`/worlds/${S.world.id}/feed`,{source:data.get('source'),content:data.get('content')});toast('Untrusted event added');},'Inject event');}
function addAgent() {if(!S.world)return toast('Create a world first'); modal('Add agent',`
  <label class="dialog-label">Name</label><input name="name" required minlength="2" maxlength="64" class="dialog-field" placeholder="e.g. Echo" />
  <label class="dialog-label">Role</label><input name="role" required minlength="3" maxlength="90" class="dialog-field" placeholder="e.g. Quality Auditor" />
  <label class="dialog-label">Persona</label><textarea name="persona" maxlength="500" class="dialog-field" rows="2" placeholder="Role objectives and guardrails"></textarea>
  <label class="dialog-label">Provider</label><select name="provider" class="dialog-field"><option value="heuristic">Deterministic (no API cost)</option><option value="openai_compatible">Configured OpenAI-compatible endpoint</option></select>
  <label class="dialog-label">Model name</label><input name="model" class="dialog-field" value="heuristic-v1" />
  <label class="dialog-label">Starting location</label><select name="location" class="dialog-field">${['Commons','Lab','Market','Hall','Library','Station'].map(s=>`<option>${s}</option>`).join('')}</select>`,async data=>{
    await post(`/worlds/${S.world.id}/agents`,{name:data.get('name'),role:data.get('role'),persona:data.get('persona'),provider:data.get('provider'),model:data.get('model'),location:data.get('location')});toast('Agent added');
  },'Add agent'); }
async function showAgent(id) {
  const a=S.agents.find(x=>x.id===id);if(!a||!S.world)return;
  let memories=[];try{memories=await api(`/worlds/${S.world.id}/agents/${a.id}/memories`);}catch(err){toast(err.message);}
  modal(`${a.name} / ${a.role}`,`
    <div class="agent-detail"><div class="detail-row"><span>Model</span><strong>${esc(a.model)}</strong></div><div class="detail-row"><span>Energy</span><strong>${a.energy}%</strong></div><div class="detail-row"><span>Credits</span><strong>${a.credits}</strong></div><div class="detail-row"><span>Location</span><strong>${esc(a.location)}</strong></div><div class="detail-row"><span>Completed turns</span><strong>${a.turns_taken}</strong></div><div class="detail-row"><span>Memory records</span><strong>${memories.length}</strong></div>
    <p class="dialog-help">${esc(a.persona)}</p><p class="dialog-help">${esc(memories.slice(0,3).map(m=>`${m.trust}: ${m.content}`).join(' • ')||'No memories yet.')}</p></div>`, async()=>{},'Close');
}
async function review(id,op) {
  if(!confirm(`${op === 'approve' ? 'Approve' : 'Reject'} this requested external action? Your authenticated key identity will be logged.`)) return;
  try{await post(`/worlds/${S.world.id}/approvals/${id}/${op}`,{});toast('Review saved');await refresh();}catch(err){toast(err.message);}
}
async function dispatch(id) {
  if(!confirm('Dispatch approved action to the server-configured external gateway?'))return;
  try{await post(`/worlds/${S.world.id}/approvals/${id}/dispatch`);toast('Dispatched');await refresh();}catch(err){toast(err.message);}
}
function keyModal() {modal('API access key',`<p class="dialog-help">Use the server-generated key from your deployment. This browser keeps it in memory only; it is not stored in localStorage.</p><label class="dialog-label">API KEY</label><input class="dialog-field" type="password" name="key" autocomplete="off" placeholder="Paste server API key" />`,async data=>{setApiKey(data.get('key'));toast('Key updated for this tab');},'Connect');}
$('create-world').onclick=createWorld;$('new-world-shortcut').onclick=createWorld;$('toggle-running').onclick=()=>toggleWorld().catch(err=>toast(err.message));
$('step-one').onclick=()=>step(1).catch(err=>toast(err.message));$('step-ten').onclick=()=>step(10).catch(err=>toast(err.message));
$('refresh').onclick=refresh;$('inject-feed').onclick=feedModal;$('add-agent').onclick=addAgent;$('open-key').onclick=keyModal;
refresh(); refreshTimer=setInterval(()=>{if(!document.hidden)refresh();},2800);
