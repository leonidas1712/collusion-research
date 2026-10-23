"""Read-only Lambda inventory; retain only capacity and non-secret account summaries."""
import json
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from dotenv import dotenv_values
from collusion.runs import REPO, start_run

BASE = 'https://cloud.lambda.ai/api/v1'
key = dotenv_values(REPO / '.env').get('LAMBDA_API_KEY')
if not key:
    raise SystemExit('LAMBDA_API_KEY is missing from .env')
run = start_run('e02-lambda-inventory', experiment='E02', settings={'base_url': BASE, 'method': 'GET', 'endpoints': ['instance-types', 'instances', 'file-systems', 'ssh-keys']})
result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'base_url': BASE}
for endpoint in ('instance-types', 'instances', 'file-systems', 'ssh-keys'):
    request = Request(f'{BASE}/{endpoint}', headers={'Authorization': f'Bearer {key}', 'Accept': 'application/json'}, method='GET')
    try:
        with urlopen(request, timeout=45) as response:
            data = json.load(response)['data']
    except (HTTPError, URLError) as error:
        result[endpoint] = {'error': type(error).__name__, 'status': getattr(error, 'code', None)}
        if isinstance(error, HTTPError):
            try:
                problem = json.loads(error.read())
                result[endpoint]['error_code'] = problem.get('error_code')
                result[endpoint]['error_name'] = problem.get('error_name')
                if problem.get('retryable') is False:
                    result['stopped_after'] = endpoint
                    break
            except (ValueError, TypeError):
                pass
        time.sleep(1.1)
        continue
    if endpoint == 'instance-types':
        result[endpoint] = data
    elif endpoint == 'ssh-keys':
        result[endpoint] = [{'name': item.get('name')} for item in data]
    elif endpoint == 'instances':
        result[endpoint] = [{'name': item.get('name'), 'status': item.get('status'), 'region': item.get('region'), 'instance_type': item.get('instance_type', {}).get('name')} for item in data]
    else:
        result[endpoint] = [{k: item.get(k) for k in ('name', 'region', 'is_in_use', 'bytes_used')} for item in data]
    time.sleep(1.1)
(run.dir / 'inventory.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
print('Run:', run.id)
run.result(endpoints_checked=sum(e in result for e in ('instance-types', 'instances', 'file-systems', 'ssh-keys')), errors=sum(isinstance(v, dict) and 'error' in v for v in result.values()))
