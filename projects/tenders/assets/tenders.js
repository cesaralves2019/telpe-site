/* Telpe Tenders — shared behaviour for how.html, try.html, pricing.html (and the landing's modal).
   Sample notices + fit scoring + phone previews + the "Start" sheet. Every piece checks that its
   elements exist, so one file serves all pages. Nothing here sends or stores anything. */
(function(){
'use strict';
/* When the bots are live, put the real links here and the Start sheet switches from preview to real. */
const LINKS={whatsapp:'',telegram:''};
document.querySelectorAll('#year').forEach(el=>el.textContent=new Date().getFullYear());
const NOW=new Date();
const DAY=864e5;
const iso=d=>new Date(NOW.getTime()+d*DAY).toISOString().slice(0,10); /* sample deadlines are relative to today so the preview never goes stale */
const SECTORS={construction:'Construction & civil works',cleaning:'Cleaning & facilities',it:'IT & software',consultancy:'Consultancy & engineering',catering:'Catering & food',landscaping:'Landscaping & grounds',transport:'Transport & fleet',security:'Security',training:'Training & education',printing:'Printing & marketing'};
const REGION_GROUP={dublin:['dublin'],leinster:['dublin','leinster'],munster:['munster'],connacht:['connacht'],ni:['ni'],uk:['uk'],all:['dublin','leinster','munster','connacht','ireland'],'ie-uk':['dublin','leinster','munster','connacht','ireland','ni','uk']};
const SRC={et:'eTenders',ted:'TED',cf:'Contracts Finder',fat:'Find a Tender',pcs:'Public Contracts Scotland',ni:'eSourcing NI'};
/* Sample notices for the preview: shaped like real ones, but illustrative. Buyers are real public bodies; the notices are not. */
const T=[
  {buyer:'Dublin City Council',title:'Grounds maintenance of parks and open spaces, North Central Area',sector:'landscaping',region:'dublin',value:420000,cur:'€',close:iso(19),src:'et',sub:false,kw:'parks mowing hedging litter grounds',sum:'Three years plus two optional extensions. Mowing, hedging and litter across 42 sites. Needs €6.5m public liability and two references of similar scale.'},
  {buyer:'HSE',title:'Contract cleaning services, community healthcare facilities, Dublin South',sector:'cleaning',region:'dublin',value:1200000,cur:'€',close:iso(25),src:'et',sub:false,kw:'cleaning healthcare clinics',sum:'Eleven primary-care centres, daily cleaning and periodic deep cleans. HSE infection-control standards; staff Garda vetting required.'},
  {buyer:'Fingal County Council',title:'Supply and installation of playground equipment, Swords and Balbriggan',sector:'construction',region:'dublin',value:310000,cur:'€',close:iso(12),src:'et',sub:false,kw:'playground equipment installation parks',sum:'Two playgrounds, design-and-install. EN 1176 certified equipment, 12-month defects period. Site visits the week before closing.'},
  {buyer:'TU Dublin',title:'Managed print services, all campuses',sector:'it',region:'dublin',value:850000,cur:'€',close:iso(32),src:'et',sub:false,kw:'print printers managed services',sum:'Five-year managed print across Grangegorman, Tallaght and Blanchardstown. Device fleet, follow-me printing, quarterly reporting.'},
  {buyer:'Cork County Council',title:'Road markings and lining, county-wide, 2027 to 2029',sector:'construction',region:'munster',value:2400000,cur:'€',close:iso(39),src:'ted',sub:false,kw:'road markings lining thermoplastic',sum:'Three-year framework, three lots by division. Thermoplastic and paint, night working. NRA-approved materials only.'},
  {buyer:'Galway City Council',title:'Catering services for City Hall and civic events',sector:'catering',region:'connacht',value:180000,cur:'€',close:iso(16),src:'et',sub:true,kw:'catering events canteen',sum:'Two-year contract for council meetings and about 30 civic events a year. HACCP required; Irish-sourced produce scored.'},
  {buyer:'Office of Public Works',title:'Conservation stonework, Kilkenny Castle west wing',sector:'construction',region:'leinster',value:640000,cur:'€',close:iso(23),src:'et',sub:false,kw:'stonework conservation heritage masonry',sum:'Repointing and stone replacement on a protected structure. Conservation-accredited contractor; lime mortar only; 40-week programme.'},
  {buyer:'Department of Education',title:'Framework for digital-skills training for school leaders',sector:'training',region:'ireland',value:500000,cur:'€',close:iso(46),src:'et',sub:false,kw:'training digital skills schools workshops',sum:'National framework, four lots by region. Blended delivery, evaluation reports per cohort. Trainers need QQI level 8 or equivalent.'},
  {buyer:'Limerick City and County Council',title:'Security services for civic buildings and car parks',sector:'security',region:'munster',value:720000,cur:'€',close:iso(29),src:'et',sub:false,kw:'security guarding car parks patrol',sum:'Static guarding and mobile patrols, 24/7 at three sites. PSA licence mandatory; TUPE applies to current staff.'},
  {buyer:'Iarnród Éireann',title:'Vegetation management along the rail network, Western region',sector:'landscaping',region:'connacht',value:1500000,cur:'€',close:iso(37),src:'ted',sub:false,kw:'vegetation trees cutting rail grounds',sum:'Lineside vegetation control, Athlone to Galway and Westport. Rail safety-critical training for all operatives; night possessions.'},
  {buyer:'Dún Laoghaire-Rathdown County Council',title:'Website redesign and content management system',sector:'it',region:'dublin',value:140000,cur:'€',close:iso(18),src:'et',sub:true,kw:'website cms design accessibility',sum:'Redesign of the council site on an open-source CMS. WCAG 2.2 AA, Irish-language parity, two years of support.'},
  {buyer:'Belfast City Council',title:'Cleaning of leisure centres',sector:'cleaning',region:'ni',value:950000,cur:'£',close:iso(31),src:'ni',sub:false,kw:'cleaning leisure centres',sum:'Seven leisure centres, four years. Living Wage required; social-value weighting of 10%.'},
  {buyer:'Manchester City Council',title:'Supply of catering equipment for schools',sector:'catering',region:'uk',value:220000,cur:'£',close:iso(24),src:'cf',sub:false,kw:'catering equipment kitchens schools',sum:'Commercial kitchen equipment for 18 primary schools, supply and install over the Christmas break.'},
  {buyer:'Scottish Water',title:'Engineering consultancy, small projects framework',sector:'consultancy',region:'uk',value:3000000,cur:'£',close:iso(44),src:'pcs',sub:false,kw:'engineering consultancy civil water',sum:'Four-year framework for civil and MEICA design under £500k per project. Chartered engineers; ISO 9001.'},
  {buyer:'Mayo County Council',title:'Printing of council publications and signage',sector:'printing',region:'connacht',value:90000,cur:'€',close:iso(15),src:'et',sub:true,kw:'printing signage publications',sum:'Two-year contract, call-off basis. Annual report, newsletters, outdoor signage. Irish-language proofs required.'},
  {buyer:'Tusla',title:'Lease of fleet vehicles, 40 units',sector:'transport',region:'ireland',value:1100000,cur:'€',close:iso(40),src:'et',sub:false,kw:'fleet vehicles lease cars vans',sum:'Four-year operating lease, 40 cars and vans, nationwide delivery. Full maintenance, electric preferred.'},
  {buyer:'Waterford City and County Council',title:'Energy consultancy for public-buildings retrofit',sector:'consultancy',region:'munster',value:260000,cur:'€',close:iso(22),src:'et',sub:false,kw:'energy retrofit consultancy BER',sum:'Energy audits and retrofit design for 14 buildings. SEAI-registered assessors; deliverables to 2030 targets.'},
  {buyer:'Wexford County Council',title:'Leisure-centre cleaning and caretaking',sector:'cleaning',region:'leinster',value:380000,cur:'€',close:iso(33),src:'et',sub:false,kw:'cleaning caretaking leisure',sum:'Two leisure centres, three years. Early and late shifts; pool-hall cleaning standards.'}
];
const fmtMoney=(v,c)=>c+(v>=1e6?(v/1e6).toFixed(1).replace(/\.0$/,'')+'m':Math.round(v/1000)+'k');
const fmtClose=iso=>{const d=new Date(iso+'T17:00:00');return d.toLocaleDateString('en-IE',{weekday:'short',day:'numeric',month:'short'});};
const daysLeft=iso=>Math.max(0,Math.ceil((new Date(iso+'T17:00:00')-NOW)/DAY));
const valueBand=v=>v<100000?'s':v<500000?'m':v<2e6?'l':'xl';
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const portalLink=t=>({et:'https://www.etenders.gov.ie',ted:'https://ted.europa.eu',cf:'https://www.contractsfinder.service.gov.uk',fat:'https://www.find-tender.service.gov.uk',pcs:'https://www.publiccontractsscotland.gov.uk',ni:'https://etendersni.gov.uk'}[t.src]);

/* ---------- Matcher ---------- */
let sel=new Set(['landscaping','cleaning']),mode='alert';
const $=id=>document.getElementById(id);
function buildSectors(){$('sectors').innerHTML=Object.entries(SECTORS).map(([k,v])=>`<button type="button" data-s="${k}" class="${sel.has(k)?'on':''}">${v}</button>`).join('');}
const hasMatcher=!!$('sectors');
if(hasMatcher){
  $('sectors').addEventListener('click',e=>{const b=e.target.closest('[data-s]');if(!b)return;const k=b.dataset.s;sel.has(k)?sel.delete(k):sel.add(k);buildSectors();render();});
  ['region','value','kw','sub'].forEach(id=>$(id).addEventListener('input',render));
}
function match(){
  const region=$('region').value,band=$('value').value,sub=$('sub').checked,kws=$('kw').value.toLowerCase().split(/[,\s]+/).filter(w=>w.length>2);
  const regions=REGION_GROUP[region];
  return T.map(t=>{
    let fit=0;const reasons=[];
    if(sel.size===0||sel.has(t.sector))fit+=60;else return null;
    if(regions.includes(t.region)||(t.region==='ireland'&&region!=='uk'&&region!=='ni'))fit+=20;else return null;
    if(band==='any'||valueBand(t.value)===band)fit+=10;else fit-=25;
    const hits=kws.filter(w=>(t.title+' '+t.kw+' '+t.sum).toLowerCase().includes(w));fit+=Math.min(15,hits.length*8);if(kws.length&&!hits.length)fit-=15;
    if(t.sub&&!sub)return null;
    const dl=daysLeft(t.close);if(dl<=3)fit-=10;
    fit=Math.max(35,Math.min(98,fit+((t.buyer.length*7)%6)));
    return {...t,fit,dl};
  }).filter(Boolean).sort((a,b)=>b.fit-a.fit||a.dl-b.dl);
}
let top=null;
function render(){
  const list=match();top=list[0]||null;
  const r=$('results');
  if(!list.length){r.innerHTML='<div class="empty">Nothing fits those filters in the sample set. Loosen the size or add a sector.</div>';renderPreview();return;}
  r.innerHTML=`<div class="count"><span><b class="num">${list.length}</b> of ${T.length} sample notices fit · sorted by fit</span><span>Sub-threshold notices marked in orange</span></div>`+list.map((t,i)=>`<div class="tender ${i===0?'pick':''}"><div><div class="buyer"><span>${esc(t.buyer)}</span><span class="src ${t.sub?'sub':''}">${t.sub?'sub-threshold · ':''}${SRC[t.src]}</span></div><h3>${esc(t.title)}</h3><div class="meta"><span>Est. <b class="num">${fmtMoney(t.value,t.cur)}</b></span><span class="deadline ${t.dl<=5?'urgent':t.dl<=10?'soon':''}">Closes <b class="num">${fmtClose(t.close)}</b> · ${t.dl} days</span></div></div><div class="fit"><b class="num">${t.fit}%</b><span>fit</span></div></div>`).join('');
  renderPreview();
}
function bubble(html,me,time){return `<div class="bub ${me?'me':''}">${html}<span class="t">${time||''}</span></div>`;}
function alertText(t){return `<b>New tender · ${esc(t.buyer)}</b>\n${esc(t.title)}\n\nEst. ${fmtMoney(t.value,t.cur)} · closes ${fmtClose(t.close)} (${t.dl} days)\nFit ${t.fit}% for ${SECTORS[t.sector].toLowerCase()}${t.sub?' · sub-threshold, eTenders only':''}\n\n${esc(t.sum)}\n\n<span class="link">${portalLink(t).replace('https://','')}</span>\n\nReply SAVE to track · MORE for the next`;}
function renderPreview(){
  const th=$('preview-thread');const hhmm=`${String(NOW.getHours()).padStart(2,'0')}:${String(NOW.getMinutes()).padStart(2,'0')}`;
  if(!top){th.innerHTML='<div class="date">Today</div>'+bubble('No new tenders fit your profile today. Nothing to read, nothing missed.',false,hhmm);return;}
  const list=match().slice(0,4);
  if(mode==='alert'){th.innerHTML='<div class="date">Today</div>'+bubble(alertText(top),false,'08:05')+bubble('SAVE',true,'08:12')+bubble(`Saved. I'll remind you 7 days and 2 days before ${fmtClose(top.close)}.`,false,'08:12');}
  else if(mode==='digest'){th.innerHTML='<div class="date">Monday</div>'+bubble(`<b>Your week in tenders · ${list.length} that fit</b>\n\n`+list.map((t,i)=>`${i+1}. ${esc(t.buyer)} · ${esc(t.title)}\n   ${fmtMoney(t.value,t.cur)} · closes ${fmtClose(t.close)} · fit ${t.fit}%`).join('\n\n')+`\n\nReply a number for the summary and link.`,false,'08:00')+bubble('1',true,'08:03')+bubble(alertText(list[0]),false,'08:03');}
  else{const t=top;th.innerHTML='<div class="date">'+fmtClose(new Date(new Date(t.close+'T17:00:00')-7*DAY).toISOString().slice(0,10))+'</div>'+bubble(`<b>7 days left · ${esc(t.buyer)}</b>\n${esc(t.title)}\n\nCloses ${fmtClose(t.close)} at 17:00. Clarification questions usually close a week before; check the notice.\n\n<span class="link">${portalLink(t).replace('https://','')}</span>`,false,'09:00')+bubble(`<b>2 days left · ${esc(t.buyer)}</b>\n${esc(t.title)}\n\nSubmission is on the portal, not by email. Upload early; eTenders gets slow on deadline afternoons.`,false,'09:00');}
}
if(hasMatcher){
  document.querySelector('.modes').addEventListener('click',e=>{const b=e.target.closest('[data-mode]');if(!b)return;mode=b.dataset.mode;document.querySelectorAll('.modes button').forEach(x=>x.classList.toggle('on',x===b));renderPreview();});
  $('send').addEventListener('click',()=>{const v=$('phone').value.trim();$('send-ok').textContent=v?`Noted. In the real product the bot would message ${v} now to confirm. This is a preview: nothing was sent.`:'Add your number first.';});
}

/* ---------- Hero & anatomy phones ---------- */
function heroThread(){
  const a=T[0],b=T[2];const da=daysLeft(a.close),db=daysLeft(b.close);
  $('hero-thread').innerHTML='<div class="date">Today</div>'+bubble(`<b>New tender · ${esc(a.buyer)}</b>\n${esc(a.title)}\n\nEst. ${fmtMoney(a.value,a.cur)} · closes ${fmtClose(a.close)} (${da} days)\nFit 92% for landscaping\n\n${esc(a.sum)}\n\n<span class="link">etenders.gov.ie</span>`,false,'08:05')+bubble('SAVE',true,'08:12')+bubble(`Saved. I'll remind you 7 days and 2 days before ${fmtClose(a.close)}.`,false,'08:12')+bubble(`<b>Also today · ${esc(b.buyer)}</b>\n${esc(b.title)} · ${fmtMoney(b.value,b.cur)} · closes ${fmtClose(b.close)} (${db} days) · fit 71%\nReply MORE for the summary.`,false,'08:05');
}
function anatomyThread(){const t=T[6];$('anatomy-thread').innerHTML='<div class="date">Today</div>'+bubble(`<b>New tender · ${esc(t.buyer)}</b>  <i style="font-style:normal;color:#1f6b45">①</i>\n${esc(t.title)}\n\nEst. ${fmtMoney(t.value,t.cur)} · closes ${fmtClose(t.close)} (${daysLeft(t.close)} days)  <i style="font-style:normal;color:#1f6b45">②</i>\n\n${esc(t.sum)}  <i style="font-style:normal;color:#1f6b45">③</i>\n\nFit 88% for construction · heritage  <i style="font-style:normal;color:#1f6b45">④</i>\n\n<span class="link">etenders.gov.ie</span>\nReply SAVE · MORE · STOP  <i style="font-style:normal;color:#1f6b45">⑤</i>`,false,'08:05');}

/* ---------- Start (preview) ---------- */
const modal=$('modal');
if(modal){
  const open=()=>{modal.classList.add('open');modal.querySelector('.channel').focus();};
  const close=()=>modal.classList.remove('open');
  document.querySelectorAll('[data-start]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();open();}));
  $('modal-x').addEventListener('click',close);
  modal.addEventListener('click',e=>{if(e.target===modal)close();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
  modal.querySelectorAll('.channel').forEach(a=>{
    const link=LINKS[a.dataset.channel];
    if(link){a.href=link;a.target='_blank';a.rel='noopener';}
    else a.addEventListener('click',e=>{e.preventDefault();$('modal-fine').textContent=`Preview: the ${a.dataset.channel==='whatsapp'?'WhatsApp':'Telegram'} bot isn't live yet. Nothing was sent, nothing was stored.`;});
  });
}
if(hasMatcher){buildSectors();render();}
if($('hero-thread'))heroThread();
if($('anatomy-thread'))anatomyThread();
})();
