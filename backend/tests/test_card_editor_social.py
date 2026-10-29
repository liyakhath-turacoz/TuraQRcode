import base64
import csv
import io
import zipfile
from pathlib import Path

import pytest
import zxingcpp
from PIL import Image
from pypdf import PdfReader
import resvg_py

from app.qr import render
from app.schemas import Design, validate_content
from app.social import social_url


@pytest.mark.parametrize('platform,value,expected',[
    ('youtube','@turacoz','https://www.youtube.com/@turacoz'),
    ('youtube','turacoz','https://www.youtube.com/@turacoz'),
    ('youtube','youtube.com/@turacoz','https://youtube.com/@turacoz'),
    ('youtube','channel/UCUZHFZ9jIKrLroW8LcyJEQQ','https://www.youtube.com/channel/UCUZHFZ9jIKrLroW8LcyJEQQ'),
    ('youtube','UCUZHFZ9jIKrLroW8LcyJEQQ','https://www.youtube.com/channel/UCUZHFZ9jIKrLroW8LcyJEQQ'),
    ('youtube','user/YouTube','https://www.youtube.com/user/YouTube'),
    ('youtube','https://youtu.be/dQw4w9WgXcQ?t=5','https://youtu.be/dQw4w9WgXcQ?t=5'),
    ('youtube','https://www.youtube.com/','https://www.youtube.com/'),
    ('instagram','@turacoz','https://www.instagram.com/turacoz'),
    ('instagram','turacoz.research','https://www.instagram.com/turacoz.research'),
    ('facebook','turacoz','https://www.facebook.com/turacoz'),
    ('linkedin','morgan-lee','https://www.linkedin.com/in/morgan-lee'),
    ('linkedin','company/turacoz','https://www.linkedin.com/company/turacoz'),
    ('x','@turacoz','https://x.com/turacoz'),
    ('tiktok','@turacoz','https://www.tiktok.com/@turacoz'),
    ('github','turacoz','https://github.com/turacoz'),
    ('pinterest','turacoz','https://www.pinterest.com/turacoz'),
    ('telegram','@turacoz','https://t.me/turacoz'),
    ('whatsapp','+919876543210','https://wa.me/919876543210'),
    ('whatsapp','+91 (987) 654-3210','https://wa.me/919876543210'),
])
def test_social_handles_and_urls(platform,value,expected):
    assert social_url(platform,value)==expected


@pytest.mark.parametrize('value',['https://youtube.com.evil.com/@name','https://evil.com/youtube.com/name',
    'javascript:alert(1)','https://name:password@youtube.com/@name','A Display Name','@name/../evil','https://youtube.com:8080/name','name\\evil',''])
def test_social_handles_reject_ambiguous_or_unsafe_destinations(value):
    with pytest.raises(ValueError):
        social_url('youtube',value)


@pytest.mark.parametrize('kind',['youtube','instagram','facebook','linkedin'])
def test_social_handle_preview_saved_qr_redirect_edit_and_exports(client,member,kind):
    expected=social_url(kind,'@turacoz')
    body={'kind':kind,'content':{'url':'@turacoz'}}
    image=client.post('/api/qr/preview?format=png&size=354',json=body)
    assert image.status_code==200,image.text
    assert zxingcpp.read_barcode(Image.open(io.BytesIO(image.content))).text==expected
    static=client.post('/api/codes',json={'name':'Handle '+kind,'mode':'static',**body}).json()
    assert static['content']['url']==expected and static['qr_payload']==expected
    editable=client.post('/api/codes',json={'name':'Editable handle '+kind,'mode':'dynamic',**body}).json()
    assert client.get(editable['qr_payload'],follow_redirects=False).headers['location']==expected
    update=client.patch('/api/codes/'+editable['id'],json={'content':{'url':'@newprofile'}})
    assert update.status_code==200,update.text
    assert client.get(editable['qr_payload'],follow_redirects=False).headers['location']==social_url(kind,'@newprofile')
    for fmt,mime in [('png','image/png'),('svg','image/svg+xml'),('pdf','application/pdf')]:
        result=client.get('/api/codes/'+static['id']+'/download?format='+fmt)
        assert result.status_code==200 and mime in result.headers['content-type']


def test_rich_profile_formatting_is_safe_and_persists(client,member):
    bio='<p><strong>Medical</strong> <em>research</em> <u>leader</u><sup>2</sup></p><ul><li><p>First service</p></li></ul>'
    response=client.post('/api/cards',json={'name':'Morgan Lee','bio':'Fallback','bio_html':bio,
        'sections':[{'title':'Expertise','body':'Fallback','body_html':'<p><s>Old</s> <code>New</code></p>'}],
        'experience':[{'role':'Director','description_html':'<p>H<sub>2</sub>O research</p>'}],
        'social_links':[{'platform':'youtube','url':'@turacoz'},{'platform':'linkedin','url':'company/turacoz'}]})
    assert response.status_code==201,response.text
    card=response.json()
    assert card['bio']=='Medical research leader2\nFirst service'
    assert card['experience'][0]['description']=='H2O research'
    assert card['social_links'][0]['url']=='https://www.youtube.com/@turacoz'
    public=client.get('/c/'+card['slug'])
    assert bio in public.text and '<sub>2</sub>' in public.text
    assert 'profile-panel' not in public.text
    assert public.text.count('TuraQRcode by Turacoz')==1
    harmful='<p onclick="evil()">Safe<img src=x onerror="evil()"><script>bad()</script><svg onload="evil()"></svg><a href="javascript:evil()">link</a></p>'
    updated=client.patch('/api/cards/'+card['id'],json={'name':'Morgan Lee','bio_html':harmful}).json()
    assert updated['bio']=='Safelink'
    assert updated['bio_html']=='<p>Safelink</p>'
    assert 'evil()' not in client.get('/c/'+card['slug']).text
    legacy=client.patch('/api/cards/'+card['id'],json={'name':'Morgan Lee','bio':'<script>plain text</script>\nNext line'}).json()
    assert legacy['bio_html']==''
    assert '&lt;script&gt;plain text&lt;/script&gt;<br>Next line' in client.get('/c/'+card['slug']).text
    assert client.post('/api/cards',json={'name':'Too long','bio_html':'<p>'+('a'*2001)+'</p>'}).status_code==422


def image_data(size):
    output=io.BytesIO();Image.new('RGB',size,'#2563eb').save(output,'PNG')
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()


def test_card_image_dimensions_limits_and_aspect_ratios(client,member):
    malformed=client.post('/api/cards',json={'name':'Invalid image','profile_image':'data:image/png;base64,!!'})
    assert malformed.status_code==422 and 'could not be opened' in malformed.json()['detail']
    body={'name':'Image limits','profile_image':image_data((640,480)),'cover_image':image_data((1600,900)),'company_logo':image_data((600,200))}
    result=client.post('/api/cards',json=body)
    assert result.status_code==201,result.text
    card=result.json()
    for key,expected in [('profile_image',(512,512)),('cover_image',(1280,720)),('company_logo',(512,512))]:
        loaded=Image.open(io.BytesIO(base64.b64decode(card[key].split(',')[1])))
        assert loaded.size==expected
        if key=='company_logo':
            bounds=loaded.convert('RGBA').getchannel('A').getbbox()
            assert bounds[2]-bounds[0]==512 and 169<=bounds[3]-bounds[1]<=172
    for key,size in [('profile_image',(127,128)),('cover_image',(319,180)),('company_logo',(63,64)),('cover_image',(2200,2000))]:
        assert client.post('/api/cards',json={'name':'Invalid image',key:image_data(size)}).status_code==422


def test_complete_card_payload_and_request_boundaries(client,member):
    import json
    from PIL.PngImagePlugin import PngInfo
    metadata=PngInfo();metadata.add_text('Description','x'*450000)
    output=io.BytesIO();Image.new('RGB',(640,360),'#2563eb').save(output,'PNG',pnginfo=metadata)
    media='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
    body={'name':'Complete professional card','profile_image':media,'cover_image':media,'company_logo':media,
        'bio_html':'<p>'+('<b></b>'*3800)+'Professional bio</p>',
        'sections':[{'title':'Section '+str(i),'body':'Section text','body_html':'<p>'+('<strong></strong>'*900)+'Section text</p>'} for i in range(10)],
        'experience':[{'role':'Role '+str(i),'description_html':'<p>'+('<i></i>'*2000)+'Experience</p>'} for i in range(12)]}
    raw=json.dumps(body).encode()
    assert 2_000_000<len(raw)<3_000_000
    result=client.post('/api/cards',content=raw,headers={'Content-Type':'application/json'})
    assert result.status_code==201,result.text
    assert client.post('/api/cards',content=b' '*3_000_001).status_code==413
    assert client.post('/api/qr/preview',content=b' '*2_000_001).status_code==413


def test_actual_five_row_csv_creates_decodable_codes_and_short_links(client,member):
    path=Path(__file__).resolve().parents[2]/'frontend/public/examples/bulk-5.csv'
    rows=list(csv.DictReader(path.read_text(encoding='utf-8').splitlines()))
    assert len(rows)==5
    for mode in ('dynamic','short','static'):
        response=client.post('/api/codes/bulk',json={'rows':[{'name':row['name'],'mode':mode,'content':{'url':row['url']}} for row in rows]})
        assert response.status_code==200,response.text
        assert response.json()['created']==5
        codes=[item['code'] for item in response.json()['results']]
        default=next(p for p in client.get('/api/projects').json() if p['is_default'])
        assert all(code['project_id']==default['id'] for code in codes)
        for code,row in zip(codes,rows):
            if mode!='static':
                assert client.get(code['short_url'],follow_redirects=False).headers['location']==row['url']
        if mode!='short':
            bundle=client.post('/api/export/bundle',json={'ids':[c['id'] for c in codes]})
            assert bundle.status_code==200
            with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
                images=[name for name in archive.namelist() if name.endswith('.png')]
                assert len(images)==5
                assert all(zxingcpp.read_barcode(Image.open(io.BytesIO(archive.read(name)))) for name in images)


@pytest.mark.parametrize('pattern',['square','rounded','dots','soft','diamond','horizontal','vertical'])
def test_small_logo_qr_styles_decode_without_upscaled_raster(pattern):
    logo=image_data((512,512))
    for frame in ('none','scan','banner','border'):
        design=Design(pattern=pattern,eye_frame_style='rounded',eye_ball_style='circle',logo=logo,frame=frame,top_text='WELCOME',bottom_text='SCAN ME').model_dump()
        for size in (256,354,1024):
            raw,_=render('https://example.com/small-logo',design,'png',size)
            image=Image.open(io.BytesIO(raw))
            assert image.size==(size,size)
            result=zxingcpp.read_barcode(image)
            assert result and result.text=='https://example.com/small-logo',(pattern,frame,size)


@pytest.mark.parametrize('kind,content',[
    ('url',{'url':'https://example.com/contact'}),('text',{'text':'Hello from Turacoz'}),
    ('email',{'email':'hello@example.com','subject':'Hello','body':'Please get in touch.'}),
    ('phone',{'phone':'+919876543210'}),('sms',{'phone':'+919876543210','message':'Hello'}),
    ('wifi',{'ssid':'Office;Guest','password':'hello:world','security':'WPA','hidden':True}),
    ('vcard',{'name':'Taylor Morgan','company':'Turacoz','email':'taylor@example.com','phone':'+919876543210'}),
    ('upi',{'pa':'shop@okbank','am':'125.50','pn':'Turacoz','cu':'INR'}),
    ('form',{'url':'https://forms.example.com/signup'}),
    ('app',{'url':'https://play.google.com/store/apps/details?id=com.example','platform':'android'}),
    ('file',{'url':'https://example.com/menu.pdf'}),
    ('whatsapp',{'phone':'+919876543210','message':'Hello'}),
    ('youtube',{'url':'@turacoz'}),('instagram',{'url':'@turacoz'}),
    ('facebook',{'url':'turacoz'}),('linkedin',{'url':'company/turacoz'}),
])
def test_each_qr_type_decodes_from_png_svg_and_pdf_with_logo(client,member,kind,content):
    response=client.post('/api/codes',json={'name':'All formats '+kind,'kind':kind,'mode':'static','content':content,
        'design':{'logo':image_data((512,512)),'top_text':'TURACOZ','bottom_text':'SCAN ME','pattern':'rounded'}})
    assert response.status_code==201,response.text
    code=response.json()
    for fmt in ('png','svg','pdf'):
        result=client.get('/api/codes/'+code['id']+'/download?format='+fmt+'&size=354')
        assert result.status_code==200,result.text
        if fmt=='pdf':
            document=PdfReader(io.BytesIO(result.content))
            image=document.pages[0].images[0].image
        elif fmt=='svg':
            image=Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=result.content.decode())))
        else:
            image=Image.open(io.BytesIO(result.content))
        assert image.size==(354,354),(kind,fmt,image.size)
        decoded=zxingcpp.read_barcode(image)
        assert decoded and decoded.text.replace('\r\n','\n')==code['qr_payload'].replace('\r\n','\n'),(kind,fmt)
