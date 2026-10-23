/* Fast, dependency-free policy smoke test with mock service-worker APIs. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const code = fs.readFileSync(path.join(__dirname, '..', 'web', 'pwa.js'), 'utf8');

async function runCase({hostname, protocol, scripts = [], initialCaches = ['swing-static-v030', 'third-party']}) {
  let onLoad;
  let registered = [];
  const unregistered = [];
  const deleted = [];
  const origin = `${protocol}//${hostname}${protocol === 'https:' ? '' : ':8001'}`;
  const registrations = scripts.map((script, i) => ({
    active: {scriptURL: script}, waiting: null, installing: null,
    unregister: async () => { unregistered.push(i); return true; }
  }));
  const ctx = {
    console,
    URL,
    Set,
    navigator: {serviceWorker: {
      getRegistrations: async () => registrations,
      register: async (name) => { registered.push(name); return {}; }
    }},
    window: {
      location: {hostname, protocol, origin},
      addEventListener: (event, callback, options) => {
        assert.equal(event, 'load');
        assert.equal(options.once, true);
        onLoad = callback;
      },
      caches: {
        keys: async () => initialCaches,
        delete: async (name) => { deleted.push(name); return true; }
      }
    }
  };
  vm.runInNewContext(code, ctx, {filename: 'web/pwa.js'});
  assert.equal(typeof onLoad, 'function');
  onLoad();
  await new Promise(resolve => setImmediate(resolve));
  return {registered, unregistered, deleted};
}

(async () => {
  const local = await runCase({
    hostname: '127.0.0.1', protocol: 'http:',
    scripts: [
      'http://127.0.0.1:8001/static/sw.js',
      'http://127.0.0.1:8001/other-sw.js',
      'http://another.example/static/sw.js'
    ]
  });
  assert.deepEqual(local.registered, []);
  assert.deepEqual(local.unregistered, [0]);
  assert.deepEqual(local.deleted, ['swing-static-v030']);
  for (const hostname of ['localhost', '[::1]']) {
    const result = await runCase({hostname, protocol: 'http:', scripts: []});
    assert.deepEqual(result.registered, []);
  }
  const secure = await runCase({hostname: 'swing.example', protocol: 'https:'});
  assert.deepEqual(secure.registered, ['/static/sw.js']);
  assert.deepEqual(secure.deleted, []);
  const insecure = await runCase({hostname: 'swing.example', protocol: 'http:'});
  assert.deepEqual(insecure.registered, []);
  assert.deepEqual(insecure.deleted, []);
  console.log('PASS: local-only cleanup, unrelated SW preservation, trusted HTTPS registration');
})().catch(error => {console.error(error); process.exitCode=1;});
