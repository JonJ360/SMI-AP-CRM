'use strict';
window.apAPI=(()=>{
 const {url,key}=window.AP_CONFIG;
 const owner='b605d98f-498e-4a94-94cf-e055ed2b5fcc';
 let loaded,revision=0;
 const response=v=>({ok:true,json:async()=>v});
 function clear(){document.querySelector('.layout').hidden=true;document.querySelector('#auth').hidden=false;document.querySelector('#tbody').replaceChildren();document.querySelector('#cards').replaceChildren();document.querySelector('#invoice-dialog').close();}
 async function identity(){const current=await Shared360Session.current();if(current?.user?.id!==owner)throw Error(current?'This AP workspace is restricted to Jon.':'No active 360 session. Open AR Collections or Asset Register to use your existing account, then return here.');return current;}
 async function rpc(name,body){
  let current;try{current=await identity();}catch(e){clear();throw e;}
  const r=await fetch(url+'/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:key,Authorization:'Bearer '+current.session.access_token,'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});
  if(!r.ok){if([401,403].includes(r.status))clear();throw Error('AP access denied or update rejected ('+r.status+')');}return r.json();
 }
 function aging(due,today){if(!due||due<='1900-01-01')return 'Unknown';const days=Math.round((Date.parse(today)-Date.parse(due.slice(0,10)))/86400000);return days<=0?'Current':days<=30?'1–30':days<=60?'31–60':days<=90?'61–90':'91+';}
 async function read(company){const x=await rpc('ap_read',{p_company:company});if(!x.snapshot)throw Error('No GP snapshot published');const s=x.snapshot,today=new Date().toLocaleDateString('en-CA',{timeZone:'America/Chicago'}),state=new Map(x.workflow.map(w=>[w.id,w]));const rows=s.rows.map(r=>{const w=state.get(r.id)||{};return {...r,due:r.due>'1900-01-01'?r.due:null,hold:!!w.hold,held:!!(r.gp_hold||w.hold),note:w.note||'',selected:!!w.selected,aging:r.cents>0?aging(r.due,today):'Credit / payment'};});const sum=f=>rows.filter(f).reduce((n,r)=>n+r.cents,0);return response({rows,source:s.source,asof:s.asof,source_info:s.companies[company],aging_asof:today,net_cents:sum(()=>true),gross_cents:sum(r=>r.cents>0),credit_cents:sum(r=>r.cents<0),selected_cents:sum(r=>r.selected),persistence:'Supabase · Jon only'});}
 async function open(){
  const ticket=++revision;clear();
  try{await identity();await rpc('ap_read',{p_company:'SMI'});if(ticket!==revision)return;await loaded();if(ticket!==revision)return;document.querySelector('#auth').hidden=true;document.querySelector('.layout').hidden=false;document.querySelector('#auth-error').textContent='';}
  catch(e){if(ticket===revision){clear();document.querySelector('#auth-error').textContent=e.message;}}
 }
 function start(load){
  loaded=load;
  // Retire the old AP-only cache. Never sign the user out of their other apps.
  sessionStorage.removeItem('ap-session');
  document.querySelector('#retry-session').onclick=open;
  Shared360Session.client.auth.onAuthStateChange(event=>{if(event==='SIGNED_OUT'){revision++;clear();}setTimeout(open,0);});
  window.addEventListener('focus',open);
  open();
 }
 return {read,update:async(company,id,patch)=>response(await rpc('ap_update',{p_company:company,p_id:id,p_patch:patch})),start};
})();
