import {PGlite} from '@electric-sql/pglite';
import fs from 'node:fs';import assert from 'node:assert/strict';
const db=new PGlite();
await db.exec(`create role anon;create role authenticated;create role service_role bypassrls;create schema auth;create function auth.uid() returns uuid language sql as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;`);
await db.exec(fs.readFileSync('supabase/ap.sql','utf8'));
assert.ok(fs.existsSync('supabase/refresh.sql'),'atomic private publish migration required');
await db.exec(fs.readFileSync('supabase/refresh.sql','utf8'));
const payload={source:'GP SELECT-only snapshot',asof:new Date().toISOString(),companies:{SMI:{count:1,stable_reread:true,vendor_reconciliation:{difference_cents:0}},SFAB:{count:1,stable_reread:true,vendor_reconciliation:{difference_cents:0}}},rows:[{id:'SMI:1:TEST',company:'SMI',gp_hold:false,cents:100},{id:'SFAB:1:TEST',company:'SFAB',gp_hold:false,cents:100}]};
async function publish(p){return db.query('select ap_publish_checked($1::jsonb) as v',[JSON.stringify(p)])}
await publish(payload);
await db.exec(`set role authenticated;select set_config('request.jwt.claim.sub','b605d98f-498e-4a94-94cf-e055ed2b5fcc',false);select ap_update('SMI','SMI:1:TEST','{"selected":true,"note":"retain"}');reset role;`);
const bad=structuredClone(payload);bad.companies.SFAB.count=2;
await assert.rejects(publish(bad));
const next=structuredClone(payload);next.asof=new Date(Date.now()+100).toISOString();next.rows[0].cents=200;await publish(next);
assert.equal((await db.query(`select count(*)::int n from ap_snapshot_previous`)).rows[0].n,2);
assert.equal((await db.query(`select count(*)::int n from ap_audit`)).rows[0].n,1);
await db.exec(`set role authenticated`);
const wf=(await db.query(`select ap_read('SMI') v`)).rows[0].v.workflow[0];assert.equal(wf.selected,false);assert.equal(wf.note,'retain');
await db.exec('reset role');
for(const role of ['anon','authenticated','service_role']){
 await db.exec(`set role ${role}`);await assert.rejects(publish(next),/permission denied/);
 for(const t of ['ap_snapshot_previous','ap_refresh_receipts']) await assert.rejects(db.query('select * from '+t),/permission denied/);
 await db.exec('reset role');
}
console.log('PASS atomic two-company publish, rejected mismatch, prior retention, fingerprint invalidation, note/audit preservation, no API-role ingestion or new read rights');await db.close();
