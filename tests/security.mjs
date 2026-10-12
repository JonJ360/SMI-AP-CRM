import {PGlite} from '@electric-sql/pglite';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const db=new PGlite();
await db.exec(`create role anon; create role authenticated; create role service_role bypassrls; create schema auth; create function auth.uid() returns uuid language sql as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;`);
assert.ok(fs.existsSync('supabase/ap.sql'),'AP security migration must exist');
await db.exec(fs.readFileSync('supabase/ap.sql','utf8'));
await db.exec(`insert into public.ap_snapshot values ('SMI','{"rows":[{"id":"test","company":"SMI","cents":100,"gp_hold":false}],"source":"fixture"}',now());`);
for (const role of ['anon','authenticated','service_role']) {
 await db.exec(`set role ${role}`);
 for(const table of ['ap_snapshot','ap_workflow','ap_audit']) {
  for(const cmd of [`select * from ${table}`,`delete from ${table}`,`truncate ${table}`]) await assert.rejects(db.exec(cmd),/permission denied/);
 }
 await assert.rejects(db.query(`select ap_read('SMI')`),/permission denied|Jon only/);
 await db.exec('reset role');
}
await db.exec(`set role authenticated; select set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',false)`);
await assert.rejects(db.query(`select ap_read('SMI')`),/Jon only/);
await assert.rejects(db.query(`select ap_update('SMI','test','{"note":"bad"}')`),/Jon only/);
await db.exec(`select set_config('request.jwt.claim.sub','b605d98f-498e-4a94-94cf-e055ed2b5fcc',false)`);
assert.equal((await db.query(`select ap_read('SMI') as v`)).rows[0].v.snapshot.rows.length,1);
await db.query(`select ap_update('SMI','test','{"selected":true}')`);
await db.query(`select ap_update('SMI','test','{"hold":true}')`);
assert.equal((await db.query(`select ap_read('SMI') as v`)).rows[0].v.workflow[0].selected,false);
await assert.rejects(db.query(`select ap_update('SMI','test','{"selected":true}')`),/Held/);
await assert.rejects(db.query(`select ap_update('RS','test','{}')`),/Company/);
await assert.rejects(db.query(`select ap_update('SMI','test','{"cents":1}')`),/Invalid/);
await db.exec('reset role');
assert.equal((await db.query('select count(*)::int as n from ap_audit')).rows[0].n,2);
console.log('PASS: anonymous, other UID, service role denied; exact Jon RPC access; holds, validation, audit');
await db.close();
