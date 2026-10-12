import {PGlite} from '@electric-sql/pglite';
import {execFileSync} from 'node:child_process';import assert from 'node:assert/strict';import fs from 'node:fs';
const python=process.env.AP_TEST_PYTHON||'python';
const code=`import json,ap_refresh as a
from tests.test_history_validation import fixture
h=fixture();h['payments'][0]['description']="O'Brien \\u2603 \\\"quote\\\""
source={'source':'GP SELECT-only snapshot','companies':{'SMI':{'check_runs':h},'SFAB':{'check_runs':fixture('SFAB')}},'rows':[]}
app={'target_document':'TEST','amount_cents':100,'description':None}
source['companies']['SMI']['check_runs']['payments'][0]['applications']=[app,dict(app,amount_cents=200)]
print(json.dumps({'source':source,'expression':a.publish_expression(source)}))`;
const input=JSON.parse(execFileSync(python,['-c',code],{encoding:'utf8'}));
const db=new PGlite();const got=(await db.query('select '+input.expression+' as v')).rows[0].v;assert.deepEqual(got,input.source);
assert.ok(Buffer.byteLength(input.expression)<10000);
await db.close();console.log('PASS positional transport exact nested JSON/array order/quotes/Unicode/null, no DDL');
