"""Deploy an explicit public-file allowlist to the existing Vercel project.

Uses the existing CLI login. Never print tokens or deploy the workspace root.
Usage: python tools/deploy_static.py inspect|preview|production|status ID
"""
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
project = json.loads((ROOT / '.vercel/project.json').read_text())
auth = Path(os.environ['APPDATA']) / 'com.vercel.cli/Data/auth.json'
login = json.loads(auth.read_text())
# Standard refresh flow used by the official Vercel CLI. Keep tokens private.
if login.get('expiresAt', float('inf')) < time.time() + 60 and login.get('refreshToken'):
    body = urllib.parse.urlencode(dict(client_id='cl_HYyOPBNtFMfHhaUn9L4QPfTZz6TP47bp',
        grant_type='refresh_token', refresh_token=login['refreshToken'])).encode()
    req = urllib.request.Request('https://api.vercel.com/login/oauth/token', data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as response:
        renewed = json.load(response)
    login.update(token=renewed['access_token'], expiresAt=int(time.time()) + renewed['expires_in'])
    if renewed.get('refresh_token'): login['refreshToken'] = renewed['refresh_token']
    auth.write_text(json.dumps(login, indent=2))
token = login['token']
team = '?teamId=' + project['orgId']

def request(path, payload=None, headers=None, raw=False):
    data = payload if raw else (json.dumps(payload).encode() if payload is not None else None)
    h = {'Authorization': 'Bearer ' + token}
    if data is not None:
        h['Content-Type'] = 'application/octet-stream' if raw else 'application/json'
    h.update(headers or {})
    req = urllib.request.Request('https://api.vercel.com' + path + team, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read()
        return json.loads(body) if body else {}

mode = sys.argv[1]
if mode == 'inspect':
    result = request('/v9/projects/' + project['projectId'])
    print(json.dumps({'name': result['name'], 'production': result.get('targets', {}).get('production', {}).get('alias'),
                     'framework': result.get('framework')}))
elif mode == 'status':
    result = request('/v13/deployments/' + sys.argv[2])
    print(json.dumps({k: result.get(k) for k in ['id','url','readyState','alias','errorMessage']}))
else:
    if mode not in ('preview','production'):
        raise SystemExit('Expected inspect, status, preview or production')
    paths = [ROOT / p for p in ('index.html','style.css','script.js','posture-features.js','model-runtime.js','vercel.json')]
    paths += sorted((ROOT / 'assets').rglob('*'))
    files = []
    cache_path = ROOT / 'results/browser_parity/upload_cache.json'
    uploaded = set(json.loads(cache_path.read_text())) if cache_path.exists() else set()
    for path in paths:
        if not path.is_file(): continue
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix not in ('.html','.css','.js','.mjs','.wasm','.json','.task','.pdf','.tex','.md'):
            raise SystemExit('Unexpected public file: ' + relative)
        content = path.read_bytes()
        sha = hashlib.sha1(content).hexdigest()
        if sha not in uploaded:
            request('/v2/files', content, {'x-vercel-digest': sha, 'x-vercel-size': str(len(content))}, raw=True)
            uploaded.add(sha)
            cache_path.write_text(json.dumps(sorted(uploaded)))
        files.append(dict(file=relative, sha=sha, size=len(content)))
    payload = dict(name=project['projectName'], project=project['projectId'], files=files, builds=json.loads((ROOT / 'vercel.json').read_text())['builds'],
                   projectSettings=dict(framework=None, buildCommand=None, outputDirectory=None))
    if mode == 'production': payload['target'] = 'production'
    result = request('/v13/deployments', payload)
    receipt = {k: result.get(k) for k in ['id','url','readyState','alias','target']}
    receipt['public_files'] = [f['file'] for f in files]
    (ROOT / 'results/browser_parity' / (mode + '_deployment.json')).write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
