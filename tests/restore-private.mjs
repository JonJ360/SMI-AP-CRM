import {PGlite} from '@electric-sql/pglite';import fs from 'node:fs';import zlib from 'node:zlib';import assert from 'node:assert/strict';import crypto from 'node:crypto';
const file=process.argv[2];assert.ok(file,'private backup path required');const data=JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const db=new PGlite();await db.exec(`create role anon;create role authenticated;create role service_role bypassrls;create schema auth;create function auth.uid() returns uuid language sql as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;`);await db.exec(fs.readFileSync('supabase/ap.sql','utf8'));await db.exec(fs.readFileSync('supabase/refresh.sql','utf8'));
for(const table of ['ap_snapshot','ap_workflow','ap_audit']){
 for(const row of data[table]){
  const fields=Object.keys(row);const quoted=fields.map(k=>'"'+k+'"').join(',');
  await db.query(`insert into ${table}(${quoted}) ${table==='ap_audit'?'overriding system value':''} select ${quoted} from jsonb_populate_record(null::${table},$1::jsonb)`,[JSON.stringify(row)]);
 }
 const rows=(await db.query('select to_jsonb(t) v from '+table+' t')).rows.map(r=>r.v);
 const canonical=v=>JSON.stringify(v,(_k,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.entries(x).sort(([a],[b])=>a.localeCompare(b))):x);
 assert.deepEqual(rows.map(canonical).sort(),data[table].map(canonical).sort());
}
await db.exec(`set role authenticated;select set_config('request.jwt.claim.sub','b605d98f-498e-4a94-94cf-e055ed2b5fcc',false)`);
for(const company of ['SMI','SFAB']) assert.ok((await db.query('select ap_read($1) v',[company])).rows[0].v.snapshot.rows.length>0);
await db.exec('reset role;set role anon');await assert.rejects(db.query("select ap_read('SMI')"),/permission denied/);
console.log(JSON.stringify({status:'verified',target:'isolated in-memory PostgreSQL/PGlite',backup_sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),counts:Object.fromEntries(Object.entries(data).map(([k,v])=>[k,v.length])),owner_reads:true,anon_denied:true}));await db.close();
