import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const template = readFileSync(new URL('../functions/viewer-request.js.tftpl', import.meta.url), 'utf8');

function router({ state = {}, deployments = ['blue', 'green'], random = 0.5, header = 'x-postmodern-deployment' } = {}) {
  const selected = [];
  const reads = [];
  const math = Object.create(Math);
  math.random = () => random;
  const context = vm.createContext({
    Math: math,
    cf: {
      kvs: () => ({
        // AWS returns promises, including rejected promises for missing keys.
        get: async (key) => {
          reads.push(key);
          await Promise.resolve();
          if (!(key in state)) throw new Error(`Missing key: ${key}`);
          if (state[key] instanceof Error) throw state[key];
          return state[key];
        },
      }),
      selectRequestOriginById: (id) => selected.push(id),
    },
  });
  const code = template
    .replace("import cf from 'cloudfront';", '')
    .replace('${deployments_json}', JSON.stringify(deployments))
    .replace('${deployment_header_json}', JSON.stringify(header));
  vm.runInContext(code, context);
  return {
    reads,
    async route(cookies = {}) {
      const request = { uri: '/account', headers: { accept: { value: 'text/html' } }, cookies };
      const returned = await context.handler({ request });
      assert.equal(returned, request, 'the original request is returned');
      assert.equal(returned.uri, '/account');
      assert.equal(returned.headers.accept.value, 'text/html');
      assert.equal(selected.length, 1, 'one origin is selected');
      assert.equal(returned.headers[header].value, selected[0], 'cache header matches the selected origin');
      return selected[0];
    },
  };
}

test('uses the asynchronously loaded active deployment instead of the first origin', async () => {
  const instance = router({ state: { active: 'green', weight: '0', pin_cookie: 'deployment' } });
  assert.equal(await instance.route(), 'green');
  assert.deepEqual(instance.reads, ['active', 'weight', 'pin_cookie']);
});

for (const [active, random, expected] of [
  ['blue', 0.249, 'green'], ['blue', 0.25, 'blue'],
  ['green', 0.249, 'blue'], ['green', 0.25, 'green'],
]) {
  test(`25% canary from ${active} at random=${random} selects ${expected}`, async () => {
    assert.equal(await router({ state: { active, weight: '25', pin_cookie: 'deployment' }, random }).route(), expected);
  });
}

test('zero weight keeps unpinned requests on the active deployment', async () => {
  assert.equal(await router({ state: { active: 'green', weight: '0', pin_cookie: 'deployment' }, random: 0 }).route(), 'green');
});

test('100% weight selects the alternative deployment', async () => {
  assert.equal(await router({ state: { active: 'blue', weight: '100', pin_cookie: 'deployment' }, random: 0.999 }).route(), 'green');
});

test('a valid pin overrides a 100% canary', async () => {
  assert.equal(await router({ state: { active: 'blue', weight: '100', pin_cookie: 'custom-pin' } }).route({ 'custom-pin': { value: 'blue' } }), 'blue');
});

test('a valid pin can select the inactive deployment at zero weight', async () => {
  assert.equal(await router({ state: { active: 'blue', weight: '0', pin_cookie: 'custom-pin' } }).route({ 'custom-pin': { value: 'green' } }), 'green');
});

test('an invalid pin does not select an unknown origin', async () => {
  assert.equal(await router({ state: { active: 'green', weight: '0', pin_cookie: 'deployment' } }).route({ deployment: { value: 'removed' } }), 'green');
});

test('a null pin setting disables pin selection', async () => {
  assert.equal(await router({ state: { active: 'green', weight: '0', pin_cookie: 'null' } }).route({ null: { value: 'blue' } }), 'green');
});

test('missing keys use the first deployment without unhandled rejections', async () => {
  assert.equal(await router().route(), 'blue');
});

test('a rejected weight read preserves valid active and cookie settings', async () => {
  const state = { active: 'green', weight: new Error('KVS unavailable'), pin_cookie: 'deployment' };
  assert.equal(await router({ state }).route(), 'green');
  assert.equal(await router({ state }).route({ deployment: { value: 'blue' } }), 'blue');
});

test('invalid rollout values retain the safe fallback', async () => {
  assert.equal(await router({ state: { active: 'removed', weight: 'invalid', pin_cookie: 'null' } }).route(), 'blue');
});

test('one deployment remains selectable with a 100% canary weight', async () => {
  assert.equal(await router({ deployments: ['only'], state: { active: 'only', weight: '100', pin_cookie: 'deployment' }, header: 'x-custom-deployment' }).route(), 'only');
});