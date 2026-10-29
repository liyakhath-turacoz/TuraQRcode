import base64
import io
from urllib.parse import quote, urlencode
import qrcode
from PIL import Image, UnidentifiedImageError


def normalize_logo(value):
    try:
        if not value.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):
            raise ValueError()
        raw = base64.b64decode(value.split(',',1)[1], validate=True)
        if len(raw) > 500000:
            raise ValueError()
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > 4_000_000 or img.width < 8 or img.height < 8:
                raise ValueError()
            img.load()
            img.thumbnail((1024,1024),Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.convert('RGBA').save(out, 'PNG')
        return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValueError('Upload a PNG, JPG, or WebP logo smaller than 500 KB and 4 megapixels.')


def vescape(s):
    return str(s).replace('\\','\\\\').replace('\r','').replace('\n',r'\n').replace(';',r'\;').replace(',',r'\,')


def normalize_card_image(value):
    verified=normalize_logo(value)
    with Image.open(io.BytesIO(base64.b64decode(verified.split(',',1)[1]))) as image:
        for quality in (85,65,45):
            output=io.BytesIO()
            image.save(output,'WEBP',quality=quality)
            if output.tell()<=450000:
                return 'data:image/webp;base64,'+base64.b64encode(output.getvalue()).decode()
    raise ValueError('Choose a smaller profile image.')


def vcard(c):
    lines = ['BEGIN:VCARD','VERSION:3.0', 'FN:' + vescape(c['name'])]
    for key, field in [('company','ORG'),('title','TITLE'),('email','EMAIL'),('phone','TEL'),('website','URL')]:
        if c.get(key):
            lines.append(field + ':' + vescape(c[key]))
    if c.get('address'):
        lines.append('ADR:;;' + vescape(c['address']))
    return '\r\n'.join(lines + ['END:VCARD',''])


def payload(kind, c):
    if kind == 'barcode': return c['value']
    if kind == 'url': return c['url']
    if kind in ('form','app','file','youtube','instagram','facebook','linkedin'): return c['url']
    if kind == 'upi':
        return 'upi://pay?' + urlencode({key:value for key,value in {
            'pa':c['pa'],'pn':c.get('pn'),'am':c.get('am'),'cu':c.get('cu','INR'),'tn':c.get('tn')
        }.items() if value})
    if kind == 'whatsapp':
        number=''.join(char for char in c['phone'] if char.isdigit())
        return 'https://wa.me/' + number + (('?'+urlencode({'text':c['message']}) if c.get('message') else ''))
    if kind == 'text': return c['text']
    if kind == 'phone': return 'tel:' + c['phone']
    if kind == 'email':
        return 'mailto:' + quote(c['email'], safe='@.') + '?' + urlencode({k:c[k] for k in ('subject','body') if c.get(k)}, quote_via=quote)
    if kind == 'sms': return 'SMSTO:' + c['phone'] + ':' + c.get('message','')
    if kind == 'vcard': return vcard(c)
    if kind == 'wifi':
        def w(v):
            for ch in ('\\',';',',',':','"'):
                v = v.replace(ch, '\\'+ch)
            return v
        return f"WIFI:T:{c.get('security','WPA')};S:{w(c['ssid'])};P:{w(c.get('password',''))};H:{'true' if c.get('hidden') else 'false'};;"
    raise ValueError('Unsupported QR type.')


def qr_matrix(data):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=4, box_size=12)
    try:
        qr.add_data(data)
        qr.make(fit=True)
    except (ValueError, qrcode.exceptions.DataOverflowError):
        raise ValueError('This content is too long. Please shorten it and try again.')
    return qr.get_matrix()


def render_code(kind,content,design,fmt='png',size=1024,data=None,print_width_cm=None,print_preset='standard'):
    if kind=='barcode':
        from .barcodes import render_barcode
        return render_barcode({**content,'value':data} if data is not None else content,design,fmt,size)
    return render(data if data is not None else payload(kind,content),design,fmt,size,print_width_cm,print_preset)


def render(data, design, fmt='png', size=1024, print_width_cm=None, print_preset='standard'):
    from .qr_render import render as compose
    return compose(data, design, fmt, size, print_width_cm, print_preset)
