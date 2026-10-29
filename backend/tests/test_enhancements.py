import asyncio
import io
import pytest
import zxingcpp
from PIL import Image
from starlette.requests import Request
from app.routes_codes import unlock


def decode(raw):
    return zxingcpp.read_barcode(Image.open(io.BytesIO(raw)))


@pytest.mark.parametrize('pattern',['square','rounded','dots','soft','diamond','horizontal','vertical'])
@pytest.mark.parametrize('eye',['square','rounded','circle'])
def test_every_pattern_and_corner_combination_decodes(client,pattern,eye):
    value='https://example.com/campaign?id=2026'
    r=client.post('/api/qr/preview?format=png',json={'content':{'url':value},'design':{
        'pattern':pattern,'eye_style':eye,'eye_color':'#4338ca','foreground':'#163b75',
        'background':'#eff6ff','frame':'banner','frame_label':'VISIT OUR WEBSITE'}})
    assert r.status_code==200,r.text
    result=decode(r.content)
    assert result and result.text==value


@pytest.mark.parametrize('fmt,value,expected',[
    ('code128','TURA-2026-001','TURA-2026-001'),('code39','TURA-001','TURA-001'),
    ('ean13','590123412345','5901234123457'),('ean8','9638507','96385074'),
    ('upca','03600029145','036000291452')])
def test_barcode_standards_save_export_and_decode(client,member,fmt,value,expected):
    r=client.post('/api/codes',json={'name':'Label '+fmt,'kind':'barcode','mode':'static',
        'content':{'format':fmt,'value':value}})
    assert r.status_code==201,r.text
    c=r.json(); assert c['content']['value']==expected and c['project_id']
    image=client.get('/api/codes/'+c['id']+'/download')
    result=zxingcpp.read_barcode(Image.open(io.BytesIO(image.content)),formats=zxingcpp.BarcodeFormat.UPCA) if fmt=='upca' else decode(image.content)
    # ZXing 3 reports UPC-A as its identical EAN-13 representation (zero prefix).
    assert result and result.text in ((expected,'0'+expected) if fmt=='upca' else (expected,))
    for extension,magic in [('svg',b'<?xml'),('pdf',b'%PDF')]:
        assert client.get('/api/codes/'+c['id']+'/download?format='+extension).content.startswith(magic)
    assert client.get('/r/'+c['slug']).status_code==404


@pytest.mark.parametrize('content',[
    {'format':'ean13','value':'5901234123450'}, {'format':'upca','value':'hello'},
    {'format':'code39','value':'lowercase'}, {'format':'code128','value':'界'},
    {'format':'unknown','value':'123'}, {'format':'code128','value':'Hello','show_text':'false'},
])
def test_invalid_barcodes_rejected(client,content):
    assert client.post('/api/qr/preview',json={'kind':'barcode','content':content}).status_code==422


def test_default_assignment_on_create_bulk_update_and_deletion_protection(client,member):
    projects=client.get('/api/projects').json()
    assert len(projects)==1 and projects[0]['is_default']
    pid=projects[0]['id']
    assert client.delete('/api/projects/'+pid).status_code==400
    c=client.post('/api/codes',json={'name':'Default','content':{'url':'https://example.com'}}).json()
    assert c['project_id']==pid
    assert client.patch('/api/codes/'+c['id'],json={'project_id':None}).json()['project_id']==pid
    bulk=client.post('/api/codes/bulk',json={'rows':[{'name':'Bulk default','content':{'url':'https://example.com'}}]}).json()
    assert bulk['results'][0]['code']['project_id']==pid
    assert client.get('/api/projects').json()[0]['total_codes']==2


@pytest.mark.parametrize('color',['#fef08a','#ffffff','#22d3ee','#000000','#ec4899'])
def test_business_cards_allow_all_brand_colors_with_scannable_qr(client,member,color):
    c=client.post('/api/cards',json={'name':'Brand Colors','color':color}).json()
    assert c['color']==color
    profile=client.get('/c/'+c['slug']).text
    assert 'background:'+color in profile
    result=decode(client.get('/api/cards/'+c['id']+'/qr').content)
    assert result and result.text==c['public_url']


def test_protected_link_security_policy_allows_external_form_redirects(client,member):
    c=client.post('/api/codes',json={'name':'Protected','password':'Access123','content':{'url':'https://example.com'}}).json()
    r=client.get('/r/'+c['slug'])
    assert "form-action 'self' https: http:" in r.headers['content-security-policy']
    assert '<form' in client.post('/r/'+c['slug'],data={'password':'wrong'}).text
    assert client.get('/api/codes/'+c['id']).json()['total_events']==0
    assert client.post('/r/'+c['slug'],content=b'password=a&password=b',headers={'Content-Type':'application/x-www-form-urlencoded'}).status_code==400


def test_disconnected_password_submission_is_handled_without_database_work():
    async def run():
        async def receive():return {'type':'http.disconnect'}
        request=Request({'type':'http','method':'POST','path':'/r/test','headers':[(b'content-type',b'application/x-www-form-urlencoded')],
                         'client':('127.0.0.1',12345),'query_string':b''},receive)
        response=await unlock('test',request,db=None)
        assert response.status_code==408
        assert b'interrupted' in response.body
    asyncio.run(run())


def test_border_frame_preserves_scannable_quiet_zone(client):
    r=client.post('/api/qr/preview?format=png',json={'content':{'url':'https://example.com/bordered'},
        'design':{'frame':'border','pattern':'soft','eye_style':'rounded'}})
    assert r.status_code==200
    assert decode(r.content).text=='https://example.com/bordered'
