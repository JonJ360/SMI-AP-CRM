'use strict';
// Read-only rendering of owner-authorized GP payment history. No write API.
window.CheckRuns=(()=>{
 const q=s=>document.querySelector(s),e=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money=n=>(n/100).toLocaleString('en-US',{style:'currency',currency:'USD'}),unknown=v=>v||'Unknown';
 let currentCompany=null,history=null,selectedRun=null,selectedPayment=null;
 const sum=(rows,k)=>rows.reduce((s,r)=>s+(r[k]||0),0);
 const range=(r,k)=>{const a=r[k+'_min'],b=r[k+'_max'];return (a?(a===b?a:a+' – '+b):'Unknown')+(r[k+'_unknown_count']?' + unknown':'');};
 const table=(headers,rows)=>'<div class="table-wrap"><table><thead><tr>'+headers.map(x=>'<th>'+e(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
 const td=values=>'<tr>'+values.map(v=>'<td>'+v+'</td>').join('')+'</tr>';
 function toggle(show){
  for(const s of ['#cards','#aging','.workspace:not(#check-runs)','.plan-bar'])q(s).hidden=show;
  if(!q('#check-runs')){const section=document.createElement('section');section.id='check-runs';section.className='workspace';section.hidden=true;q('#source').after(section);}
  q('#check-runs').hidden=!show;
 }
 function reset(){selectedRun=null;selectedPayment=null;}
 function render(data,company){
  toggle(true);history=data.source_info.check_runs;
  q('#source').textContent='GP posted payment history · Extracted '+(data.asof?new Date(data.asof).toLocaleString():'Unknown')+' · USD functional currency · Automatic five-minute refresh while Jon’s workstation is online and signed in. '+(Date.now()-Date.parse(data.asof)>=900000?'STALE SNAPSHOT — refresh before relying on history.':'');
  if(!history){q('#check-runs').innerHTML='<p>Payment history is not available in this snapshot. Existing open AP is unchanged. Reload after the next verified refresh.</p>';currentCompany=null;return;}
  if(currentCompany!==company||!q('#cr-body')){
   currentCompany=company;reset();
   q('#check-runs').innerHTML='<div class="toolbar" style="flex-wrap:wrap"><label>Date basis<select id="cr-basis"><option value="posted_date">Posted on (GP POSTEDDT)</option><option value="document_date">Payment / check date</option><option value="gl_date">GL posting date</option></select></label><label>From<input id="cr-from" type="date"></label><label>Through<input id="cr-to" type="date"></label><label>Include unknown dates<input id="cr-unknown" type="checkbox" checked></label><button id="cr-recent">Last 90 days</button><button id="cr-all">All loaded history</button><label class="search">Search runs, vendors, checks or invoices<input id="cr-search" type="search" placeholder="Batch, audit ID, vendor or check"></label></div><p id="cr-scope" class="source"></p><div id="cr-summary" class="cards"></div><div id="cr-body"></div>';
   for(const id of ['cr-basis','cr-from','cr-to','cr-unknown','cr-search'])q('#'+id).addEventListener(id==='cr-search'?'input':'change',()=>{reset();draw();});
   q('#cr-recent').onclick=()=>recent(data.aging_asof);q('#cr-all').onclick=()=>{q('#cr-from').value='';q('#cr-to').value='';reset();draw();};
   q('#check-runs').addEventListener('click',click);recent(data.aging_asof);
  }
  const scope=history.scope;
  q('#cr-scope').textContent='Available here: '+scope.basis+' GP retains '+scope.retained_payment_count+' payments dating from '+unknown(scope.retained_first_document_date)+'; '+scope.older_excluded_count+' older payments are outside this loaded scope. Groups use company + GP posting audit ID (TRXSORCE), never batch name or same date alone. Manual / transaction payments are included. Date filters match whole groups, so totals include every payment in a matching group. Posted-on is not bank clearing or check delivery time.';
  draw();
 }
 function recent(today){const d=new Date((today||new Date().toISOString().slice(0,10))+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-89);q('#cr-from').value=d.toISOString().slice(0,10);q('#cr-to').value=today||new Date().toISOString().slice(0,10);reset();draw();}
 function filtered(){
  const basis=q('#cr-basis').value,from=q('#cr-from').value,to=q('#cr-to').value,term=q('#cr-search').value.toLowerCase(),unknownDates=q('#cr-unknown').checked;
  if(from&&to&&from>to)return [];
  const hits=new Set(history.payments.filter(p=>[p.vendor,p.vendor_id,p.document,p.voucher,p.description,...p.applications.map(a=>a.target_document)].join(' ').toLowerCase().includes(term)).map(p=>p.run_id));
  return history.runs.filter(r=>((r[basis+'_min']&&(!from||r[basis+'_max']>=from)&&(!to||r[basis+'_min']<=to))||(unknownDates&&r[basis+'_unknown_count']>0))&&(!term||[r.audit,...r.batches,...r.checkbooks].join(' ').toLowerCase().includes(term)||hits.has(r.id))).sort((a,b)=>(b[basis+'_max']||'').localeCompare(a[basis+'_max']||'')||a.id.localeCompare(b.id));
 }
 function draw(){
  if(!history||!q('#cr-body'))return;
  const runs=filtered();q('#cr-summary').innerHTML=[['Cash payments · nonvoid',money(sum(runs,'cash_cents')),'Check / cash / EFT headers only'],['Posting groups',runs.length,sum(runs,'payment_count')+' payments including voids'],['Voided original amounts',money(sum(runs,'void_cents')),sum(runs,'void_count')+' voided payments excluded from cash'],['Application bridge exceptions',sum(runs,'bridge_exceptions'),'Header less remaining less applied cash']].map(([l,v,s])=>'<div class="card"><div class="eyebrow">'+e(l)+'</div><strong>'+e(v)+'</strong><small>'+e(s)+'</small></div>').join('');
  const r=history.runs.find(r=>r.id===selectedRun),p=history.payments.find(p=>p.id===selectedPayment);
  if(p&&r)return payment(p,r);
  if(r)return run(r);
  q('#cr-body').innerHTML='<p>'+runs.length+' matching posting groups. All loaded matches are shown. Cash totals exclude voids, credit-card/noncash entries, invoice applications and discounts. GP “Check” can include manually recorded wires; no banking method is inferred from the check number.</p>'+table(['Posted on','Payment / check date','Batch / GP posting audit ID','Payments','Cash total · nonvoid','Voids'],runs.map(r=>td([e(range(r,'posted_date')),e(range(r,'document_date')),'<button class="link" data-cr-run="'+e(r.id)+'">'+e(r.batches.map(unknown).join(' / '))+'</button><span class="sub">'+e(r.audit||'Unknown run ID — individual payment')+'</span>',e(r.payment_count),money(r.cash_cents),e(r.void_count)])))+(runs.length?'':'<p class="empty">No matching check runs. Adjust the date or search filters; unknown dates can be included separately.</p>');
 }
 function click(event){const b=event.target.closest('button');if(!b)return;if(b.dataset.crRun){selectedRun=b.dataset.crRun;selectedPayment=null;draw();}else if(b.dataset.crPayment){selectedPayment=b.dataset.crPayment;draw();}else if(b.id==='cr-back'){if(selectedPayment)selectedPayment=null;else selectedRun=null;draw();}}
 function run(r){
  const pp=history.payments.filter(p=>p.run_id===r.id);
  q('#cr-body').innerHTML='<button id="cr-back">← All matching runs</button><h2>'+e(r.batches.map(unknown).join(' / '))+'</h2><p>'+e(r.identity_basis)+' · '+e(r.audit||'Unknown')+' · '+e(r.sources.join(' / '))+'<br>Checkbooks: '+e(r.checkbooks.map(unknown).join(' / '))+' · Types: '+e(r.payment_types.join(' / '))+'<br>Posted on '+e(range(r,'posted_date'))+' · Payment dates '+e(range(r,'document_date'))+' · GL dates '+e(range(r,'gl_date'))+'</p><p>Cash total (nonvoid): <strong>'+money(r.cash_cents)+'</strong> · Original headers: '+money(r.original_cents)+' · Voided originals: '+money(r.void_cents)+' · Noncash / unknown type: '+money(r.noncash_cents)+'. These are GP posting groups, not proof of bank settlement. Reused batch IDs remain separate.</p>'+table(['Vendor','Check / payment','Payment date','Posted on','Type / checkbook','Original amount','Cash included','Status'],pp.map(p=>td([e(p.vendor||'Unknown vendor')+'<span class="sub">'+e(p.vendor_id)+'</span>','<button class="link" data-cr-payment="'+e(p.id)+'">'+e(p.document||p.voucher)+'</button><span class="sub">Voucher '+e(p.voucher)+'</span>',e(unknown(p.document_date)),e(unknown(p.posted_date)),e(p.payment_type_label)+'<span class="sub">'+e(unknown(p.checkbook))+'</span>',money(p.amount_cents),money(p.cash_cents),e(p.status)+(p.bridge_difference_cents?' · Bridge exception':'')])));
 }
 function payment(p,r){
  const fields=[['GP posting audit ID',r.audit],['Batch',p.batch],['Vendor / ID',(p.vendor||'Unknown')+' / '+p.vendor_id],['Payee stored on payment',p.payee],['Voucher',p.voucher],['Payment / check date (DOCDATE)',p.document_date],['Posted on (POSTEDDT)',p.posted_date],['GL posting date (PSTGDATE)',p.gl_date],['Void GL date (VOIDPDATE)',p.void_date],['Status',p.status],['Reversal linkage','Not provided by these GP sources; no linked reversal inferred'],['Payment type',p.payment_type_label],['Checkbook',p.checkbook],['Card ID',p.card],['Source currency',p.currency],['Description',p.description],['Header source',p.source_table]];
  q('#cr-body').innerHTML='<button id="cr-back">← Payments in this run</button><h2>'+e(p.document||p.voucher)+'</h2><dl>'+fields.map(([k,v])=>'<dt>'+e(k)+'</dt><dd>'+e(unknown(v))+'</dd>').join('')+'</dl><p>Original payment <strong>'+money(p.amount_cents)+'</strong> · Cash included '+money(p.cash_cents)+' · Remaining '+money(p.remaining_cents)+' · Applied cash '+money(p.applied_cents)+' · Discounts '+money(p.discount_cents)+' · Write-offs '+money(p.writeoff_cents)+'</p><p>Cash application bridge: '+(p.bridge_difference_cents===null?'Not evaluated for voided payments; historical applies are shown only when retained.':money(p.bridge_difference_cents)+' difference = original − remaining − applied cash. Discounts/write-offs are separate noncash settlement components.')+'</p><h3>Applied invoices / documents ('+p.applications.length+')</h3>'+table(['Invoice / document','Voucher / type','Invoice date','Apply date (DATE1)','Apply GL date','Applied cash','Discount','Write-off'],p.applications.map(a=>td([e(a.target_document),e(a.target_voucher)+'<span class="sub">'+e(({1:'Invoice',2:'Finance charge',3:'Misc. charge',4:'Return',5:'Credit memo'})[a.target_type]||'GP type '+a.target_type)+'</span>',e(unknown(a.target_date)),e(unknown(a.apply_date)),e(unknown(a.apply_gl_date)),money(a.amount_cents),money(a.discount_cents),money(a.writeoff_cents)])))+(p.applications.length?'':'<p class="empty">No retained posted applications for this payment. It may be unapplied or voided; no invoice relationship is invented.</p>')+'<p>Read-only history. No payment, approval, invoice change or bank action is available here.</p>';
 }
 return {render,toggle};
})();
