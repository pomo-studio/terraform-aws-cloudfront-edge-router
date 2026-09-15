import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import test from 'node:test';
import vm from 'node:vm';

const shared = readFileSync(new URL('../functions/routing.js.tftpl', import.meta.url), 'utf8');
function build(phase, state, selected) {
  const context = vm.createContext({
    cf: {
      kvs: () => ({ get: async (key) => {
        if (!(key in state)) throw new Error('missing');
        return state[key];
      } }),
      selectRequestOriginById: (id) => selected.push(id),
    },
  });
  const code = readFileSync(new URL('../functions/viewer-' + phase + '.js.tftpl', import.meta.url), 'utf8')
    .replace('${routing_code}', shared)
    .replace("import cf from 'cloudfront';", '')
    .replace('${deployments_json}', JSON.stringify(['blue', 'green']))
    .replace('${deployment_header_json}', JSON.stringify('x-postmodern-deployment'));
  vm.runInContext(code, context);
  return context;
}

test('original viewer request produces a pin matching the selected origin', async () => {
  const state = { active: 'blue', weight: '25', pin_cookie: 'deployment' };
  const selected = [];
  const requestFunction = build('request', state, selected);
  const responseFunction = build('response', state, selected);
  for (let i = 0; i < 128; i++) {
    const requestId = createHash('sha256').update(String(i)).digest('base64');
    const original = { headers: {}, cookies: {}, uri: '/shared-cache' };
    await requestFunction.handler({ context: { requestId }, request: structuredClone(original) });
    const response = await responseFunction.handler({
      context: { requestId }, request: original,
      response: { statusCode: 200, cookies: { application: { value: 'keep' } } },
    });
    assert.equal(response.cookies.deployment.value, selected.at(-1));
    assert.equal(response.cookies.application.value, 'keep');
  }
  assert.deepEqual(new Set(selected), new Set(['blue', 'green']));
});

test('response ignores a client-supplied deployment header', async () => {
  const context = build('response', { active: 'blue', weight: '0', pin_cookie: 'deployment' }, []);
  const response = await context.handler({
    context: { requestId: 'one' },
    request: { headers: { 'x-postmodern-deployment': { value: 'green' } }, cookies: {} },
    response: { statusCode: 200 },
  });
  assert.equal(response.cookies.deployment.value, 'blue');
});

test('response respects the configured cookie name and preserves a valid pin', async () => {
  const context = build('response', { active: 'blue', weight: '0', pin_cookie: 'custom-pin' }, []);
  const response = await context.handler({
    context: { requestId: 'one' },
    request: { headers: {}, cookies: { 'custom-pin': { value: 'green' } } },
    response: { statusCode: 200, cookies: {} },
  });
  assert.equal(Object.keys(response.cookies).length, 0);
});

test('disabled pinning does not issue a new cookie', async () => {
  const context = build('response', { active: 'blue', weight: '0', pin_cookie: 'null' }, []);
  const response = await context.handler({
    context: { requestId: 'one' }, request: { headers: {}, cookies: {} },
    response: { statusCode: 200, cookies: {} },
  });
  assert.equal(Object.keys(response.cookies).length, 0);
});