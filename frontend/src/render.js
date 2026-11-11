// Isometric projection with independently positioned user-controlled data; SVG is text-escaped.
export const escapeText = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const COLORS = ['#a78bfa','#4bd6fa','#f5b95c','#52ddb1','#f088bd','#8dacfa','#a5de76','#a4e1e3'];
const buildings = ['Commons','Lab','Market','Hall','Library','Station'];
const defaultLandmarks = {Commons:{x:48,y:48,label:'Community Square'},Lab:{x:23,y:23,label:'Innovation Lab'},Market:{x:75,y:22,label:'Trade Hall'},Hall:{x:76,y:74,label:'Assembly Hall'},Library:{x:23,y:74,label:'Knowledge Garden'},Station:{x:49,y:87,label:'Operations Hub'}};
const project = (x,y) => [450 + (x-y)*3.08, 50 + (x+y)*2.00];
function block(x,y,label,index) {
  const [cx,cy] = project(x,y);
  const h = index === 3 ? 30 : 18 + (index % 3)*7;
  const isHall = index === 3;
  const facade = isHall ? '#273d51' : '#1b3146';
  const top = isHall ? '#517a91' : '#34516b';
  return `<g class="building"><path d="M ${cx-45} ${cy} l45 -24 l45 24 l-45 24 Z" fill="#14283d" stroke="#294059" stroke-width="1"/>
    <path d="M ${cx-22} ${cy-h+7} l22 -12 l22 12 l-22 12 Z" fill="${top}" stroke="#7297ae" stroke-width="1"/>
    <path d="M ${cx-22} ${cy-h+7} l0 ${h} l22 12 l0 -${h} Z" fill="${facade}"/>
    <path d="M ${cx+22} ${cy-h+7} l0 ${h} l-22 12 l0 -${h} Z" fill="#263c53"/>
    <path d="M${cx-12} ${cy+1} l0 7 l6 3 l0 -7 Z" fill="#45d4e1" opacity=".75"/>
    <text x="${cx}" y="${cy+49}" text-anchor="middle" class="map-label">${escapeText(label)}</text>
    <circle cx="${cx}" cy="${cy-26}" r="2.1" fill="${isHall?'#d5b1ff':'#58e9c3'}" opacity=".85"/>
    </g>`;
}
export function renderMap(svg, agents, landmarks = defaultLandmarks, onSelect) {
  if (!agents?.length) { svg.innerHTML = '<text x="450" y="270" fill="#657188" text-anchor="middle">Add agents to visualize a world</text>'; return; }
  const cells = [];
  for (let x=0; x<=100; x+=10) {
    const [a,b] = project(x,0), [c,d]=project(x,100);
    cells.push(`<line x1="${a}" y1="${b}" x2="${c}" y2="${d}" class="gridline"/>`);
    const [e,f]=project(0,x), [g,h]=project(100,x);
    cells.push(`<line x1="${e}" y1="${f}" x2="${g}" y2="${h}" class="gridline"/>`);
  }
  const corners = [[0,0],[100,0],[100,100],[0,100]].map(([x,y])=>project(x,y).join(',')).join(' ');
  const land = buildings.map((name,i)=>{
    const loc=landmarks[name] || defaultLandmarks[name];
    return block(loc.x,loc.y,loc.label||name,i);
  }).join('');
  const actorCount = {};
  const actors = agents.map((a,i)=>{
    const loc=landmarks[a.location]||defaultLandmarks.Commons;
    const offset = actorCount[a.location] || 0;
    actorCount[a.location] = offset + 1;
    const x=loc.x + (offset%3-1)*5, y=loc.y + Math.floor(offset/3)*6 + 12;
    const [cx,cy]=project(x,y);
    const color = COLORS[i % COLORS.length];
    return `<g class="agent-dot" data-agent="${escapeText(a.id)}" tabindex="0" role="button" aria-label="${escapeText(a.name)} agent">
      <circle cx="${cx}" cy="${cy+3}" r="10" fill="${color}" opacity="0.14"/>
      <circle cx="${cx}" cy="${cy}" r="5.6" fill="${color}" stroke="#0b1525" stroke-width="2"/>
      <circle cx="${cx-1.8}" cy="${cy-1.7}" r="1.5" fill="#fff" opacity=".9"/>
      <text x="${cx}" y="${cy-13}" text-anchor="middle" class="agent-label">${escapeText(a.name)}</text>
      <title>${escapeText(a.name)}: ${escapeText(a.role)}. Energy ${a.energy}</title></g>`;
  }).join('');
  svg.innerHTML = `<defs><linearGradient id="world-gradient" x2="1" y2="1"><stop stop-color="#112b3b"/><stop offset="1" stop-color="#112033"/></linearGradient></defs>
    <polygon points="${corners}" fill="url(#world-gradient)" stroke="#2c5363" stroke-width="2" />
    <g>${cells.join('')}</g>${land}${actors}`;
  svg.querySelectorAll('[data-agent]').forEach(node=>{
    node.addEventListener('click',()=>onSelect(node.dataset.agent));
    node.addEventListener('keydown',e=>{ if(e.key==='Enter') onSelect(node.dataset.agent); });
  });
}
export function initials(name) { return String(name||'?').split(/\s+/).map(s=>s[0]).slice(0,2).join('').toUpperCase(); }
export function colorAt(i) { return COLORS[i % COLORS.length]; }
export function timeAgo(iso) {
  const sec=Math.max(0,Math.floor((Date.now()-Date.parse(iso))/1000));
  if(sec<60)return `${sec}s ago`;
  if(sec<3600)return `${Math.floor(sec/60)}m ago`;
  return `${Math.floor(sec/3600)}h ago`;
}
