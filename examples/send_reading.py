"""Envia uma leitura de TESTE de 1 mm para a estação inicial."""
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
payload = dict(device_code='ESP001', mac_address='84:CC:A8:12:34:56', timestamp=datetime.now(timezone.utc).isoformat(), ticks=4, mm_per_tick=.25, battery_mv=3850)
req = Request('http://127.0.0.1:5000/api/v1/readings', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
try:
    with urlopen(req, timeout=10) as response:
        print(response.read().decode())
except HTTPError as error:
    print(f'Erro {error.code}: {error.read().decode()}')
    raise SystemExit(1)
except URLError:
    print('Não foi possível conectar. Inicie python main.py antes de enviar a leitura.')
    raise SystemExit(1)
