import csv
import io
import tempfile
import unittest
from pathlib import Path
from pluviffar_backend.app import create_app

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app({'TESTING':True,'DATABASE':str(Path(self.tmp.name)/'test.db'),'ADMIN_PASS':'test-password','SECRET_KEY':'test-only'})
        self.client=self.app.test_client()
    def tearDown(self): self.tmp.cleanup()
    def auth(self):
        res=self.client.post('/admin/login',json={'username':'admin','password':'test-password'})
        self.assertEqual(res.status_code,200)
        return {'X-CSRF-Token':res.json['csrf']}
    def reading(self,stamp='2026-01-01T02:30:00Z',**kw):
        return dict(device_code='ESP001',mac_address='84:cc:a8:12:34:56',timestamp=stamp,ticks=4,**kw)
    def test_public_and_admin_authentication(self):
        for url in ('/', '/assets/app.js'):
            with self.client.get(url) as response:
                self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.get('/api/healthz').json,{'status':'ok'})
        self.assertEqual(self.client.get('/admin/devices').status_code,401)
        self.assertEqual(self.client.post('/admin/login',json={'username':'admin','password':'wrong'}).status_code,401)
        headers=self.auth()
        self.assertEqual(self.client.get('/admin/devices').status_code,200)
        self.assertEqual(self.client.post('/admin/devices',json={}).status_code,403)
        self.assertEqual(self.client.post('/admin/logout',headers=headers).status_code,200)
        self.assertEqual(self.client.get('/admin/devices').status_code,401)
    def test_ingestion_timezone_csv_and_retries(self):
        payload=self.reading()
        self.assertEqual(self.client.post('/api/v1/readings',json=payload).status_code,201)
        res=self.client.post('/api/v1/readings',json=payload)
        self.assertFalse(res.json['stored'])
        payload['ticks']=5
        self.assertEqual(self.client.post('/api/v1/readings',json=payload).status_code,409)
        dec=self.client.get('/data/location/1/daily?date=2025-12-31').json
        self.assertEqual(dec['total'],1)
        self.assertEqual(dec['points'][23]['mm'],1)
        self.assertEqual(self.client.get('/data/location/1/yearly?date=2026-01-01').json['total'],0)
        self.assertEqual(self.client.get('/data/location/1/monthly?date=2025-12-31').json['points'][30]['mm'],1)
        res=self.client.get('/data/location/1/daily?date=2025-12-31&format=csv')
        rows=list(csv.reader(io.StringIO(res.data.decode('utf-8-sig'))))
        self.assertEqual(len(rows),25)
        self.assertEqual(rows[-1][-1],'1.0')
    def test_validation_and_device_management(self):
        for ticks in [-1,1.5,True,'abc']:
            payload=self.reading();payload['ticks']=ticks
            self.assertEqual(self.client.post('/api/v1/readings',json=payload).status_code,422)
        self.assertEqual(self.client.post('/api/v1/readings',json=self.reading('2026-01-01')).status_code,422)
        self.assertEqual(self.client.post('/api/v1/readings',json=[]).status_code,422)
        headers=self.auth()
        data=dict(device_code='ESP002',mac_address='AA:BB:CC:DD:EE:FF',location_name='Estação teste',latitude=-28,longitude=-53,mm_per_tick_default=.5)
        res=self.client.post('/admin/devices',json=data,headers=headers);self.assertEqual(res.status_code,201);ident=res.json['id']
        self.assertEqual(self.client.post('/admin/devices',json=data,headers=headers).status_code,409)
        data['latitude']=100
        self.assertEqual(self.client.put(f'/admin/devices/{ident}',json=data,headers=headers).status_code,422)
        data['latitude']=-28;data['location_name']='Editada'
        self.assertEqual(self.client.put(f'/admin/devices/{ident}',json=data,headers=headers).status_code,200)
        self.assertEqual(self.client.delete(f'/admin/devices/{ident}',headers=headers).status_code,200)
        self.assertEqual(len(self.client.get('/data/locations').json),1)
        self.assertEqual(self.client.post('/api/v1/readings',json={**self.reading(),'device_code':'ESP002','mac_address':data['mac_address']}).status_code,401)
        self.assertEqual(len(self.client.get('/admin/audit').json),3)
    def test_persistence(self):
        self.client.post('/api/v1/readings',json=self.reading())
        other=create_app({'TESTING':True,'DATABASE':str(Path(self.tmp.name)/'test.db'),'ADMIN_PASS':'test-password'})
        self.assertEqual(other.test_client().get('/data/location/1/yearly?date=2025-01-01').json['total'],1)
    def test_login_rate_limit(self):
        for _ in range(10): self.client.post('/admin/login',json={})
        self.assertEqual(self.client.post('/admin/login',json={}).status_code,429)

if __name__=='__main__': unittest.main()
