"""Run against the disposable Compose CI project; stops and starts the backend."""
import json
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

base = 'http://127.0.0.1:8000'
headers = {'X-Client-Id':'ci-restart-owner','Content-Type':'application/json'}
def api(path, body=None):
    req = Request(base+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urlopen(req,timeout=5) as response:
        return json.load(response)

session = api('/api/sessions', {'metadata':{'restart_smoke':True}})['session_id']
container = subprocess.check_output(['docker','compose','ps','-q','backend'],text=True).strip()
assert container
subprocess.run(['docker','compose','stop','--timeout','25','backend'],check=True,timeout=35)
code = subprocess.check_output(['docker','inspect','--format','{{.State.ExitCode}}',container],text=True).strip()
assert code in {'0','143'}, 'Unexpected backend exit code: '+code
logs = subprocess.check_output(['docker','logs',container],stderr=subprocess.STDOUT,text=True)
assert 'Application shutdown complete.' in logs, 'Lifespan did not finish before stop'
subprocess.run(['docker','compose','start','backend'],check=True,timeout=30)
for _ in range(100):
    try:
        if api('/health/ready')['status'] == 'ready':
            break
    except (URLError, TimeoutError, ConnectionError):
        pass
    time.sleep(.5)
else:
    raise AssertionError('Backend readiness did not recover')
restored = api('/api/sessions/'+session)
assert restored['owner_id'] == 'ci-restart-owner'
assert restored['metadata']['restart_smoke'] is True
assert restored['status'] == 'active'
api('/api/sessions/'+session+'/close', {})
print('Container clean exit, restart, persistence and owner continuity: OK')
