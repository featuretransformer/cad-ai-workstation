import urllib.request, json, time

base_url = 'http://127.0.0.1:8000'
req = urllib.request.Request(f'{base_url}/api/sessions/', data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    sess = json.loads(resp.read())
session_id = sess['id']
print('Created session:', session_id)

prompt = 'Design an aluminum hex bolt M16 with 60mm length and chamfered tip'
gen_data = json.dumps({'session_id': session_id, 'prompt': prompt}).encode()
req = urllib.request.Request(f'{base_url}/api/design/generate', data=gen_data, headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    gen_res = json.loads(resp.read())

design_id = gen_res['design_id']
task_id = gen_res['task_id']
print(f'Queued task: {task_id} for design: {design_id}')

for i in range(30):
    time.sleep(2)
    with urllib.request.urlopen(f'{base_url}/api/design/{design_id}') as resp:
        d = json.loads(resp.read())
    status = d.get('status')
    valid = d.get('geometry_valid')
    dfm = d.get('dfm_score')
    print(f'[{i*2}s] Status: {status}, Valid: {valid}, DFM: {dfm}')
    if status in ('complete', 'failed'):
        print('=== FINAL RESULT ===')
        print('Status:', status)
        print('Geometry Valid:', valid)
        print('Material:', d.get('material'))
        print('DFM Score:', dfm)
        print('GLB URL:', d.get('glb_url'))
        print('STEP URL:', d.get('step_url'))
        break
