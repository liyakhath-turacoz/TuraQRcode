import base64
import io
from html import escape
from urllib.parse import quote, urlencode
import qrcode
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


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
            img.thumbnail((256,256))
            out = io.BytesIO()
            img.convert('RGBA').save(out, 'PNG')
        return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValueError('Upload a PNG, JPG, or WebP logo smaller than 500 KB and 4 megapixels.')


def vescape(s):
    return str(s).replace('\\','\\\\').replace('\r','').replace('\n',r'\n').replace(';',r'\;').replace(',',r'\,')


def vcard(c):
    lines = ['BEGIN:VCARD','VERSION:3.0', 'FN:' + vescape(c['name'])]
    for key, field in [('company','ORG'),('title','TITLE'),('email','EMAIL'),('phone','TEL'),('website','URL'),('address','ADR')]:
        if c.get(key):
            lines.append(field + ':' + vescape(c[key]))
    return '\r\n'.join(lines + ['END:VCARD',''])


def payload(kind, c):
    if kind == 'url': return c['url']
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


def render(data, design, fmt='png', size=1024):
    m = qr_matrix(data)
    n = len(m)
    cell = 12
    dim = n * cell
    frame = design.get('frame','none') == 'scan'
    height = dim + (64 if frame else 0)
    fg, bg = design.get('foreground','#12352f'), design.get('background','#ffffff')
    pattern = design.get('pattern','square')
    logo = design.get('logo')

    def finder(x,y):
        return (4 <= x < 11 and 4 <= y < 11) or (n-11 <= x < n-4 and 4 <= y < 11) or (4 <= x < 11 and n-11 <= y < n-4)

    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{round(size*height/dim)}" viewBox="0 0 {dim} {height}">', f'<rect width="100%" height="100%" fill="{bg}"/>']
    image = Image.new('RGB',(dim,height),bg)
    draw = ImageDraw.Draw(image)
    for y,row in enumerate(m):
        for x,on in enumerate(row):
            if not on: continue
            px,py = x*cell,y*cell
            if pattern == 'dots' and not finder(x,y):
                elements.append(f'<circle cx="{px+6}" cy="{py+6}" r="5.8" fill="{fg}"/>')
                draw.ellipse((px,py,px+11,py+11),fill=fg)
            else:
                rad = 3 if pattern == 'rounded' and not finder(x,y) else 0
                elements.append(f'<rect x="{px}" y="{py}" width="12" height="12" rx="{rad}" fill="{fg}"/>')
                draw.rounded_rectangle((px,py,px+11,py+11),radius=rad,fill=fg)
    if logo:
        edge = int(dim*.18)
        x,y = (dim-edge)//2,(dim-edge)//2
        elements.append(f'<rect x="{x-5}" y="{y-5}" width="{edge+10}" height="{edge+10}" rx="6" fill="{bg}"/>')
        elements.append(f'<image href="{escape(logo,quote=True)}" x="{x}" y="{y}" width="{edge}" height="{edge}"/>')
        draw.rounded_rectangle((x-5,y-5,x+edge+5,y+edge+5),radius=6,fill=bg)
        with Image.open(io.BytesIO(base64.b64decode(logo.split(',')[1]))) as mark:
            mark.thumbnail((edge,edge))
            image.paste(mark,((dim-mark.width)//2,(dim-mark.height)//2),mark if mark.mode=='RGBA' else None)
    if frame:
        elements.extend([f'<rect x="12" y="{dim}" width="{dim-24}" height="52" rx="10" fill="{fg}"/>',f'<text x="{dim//2}" y="{dim+33}" text-anchor="middle" font-family="Arial,sans-serif" font-weight="700" font-size="20" fill="{bg}">SCAN ME</text>'])
        draw.rounded_rectangle((12,dim,dim-12,dim+52),radius=10,fill=fg)
        draw.text((dim//2,dim+26),'SCAN ME',fill=bg,anchor='mm',font=ImageFont.load_default(size=20))
    elements.append('</svg>')
    if fmt == 'svg': return ''.join(elements).encode(), 'image/svg+xml'
    out = io.BytesIO()
    image = image.resize((size,round(size*height/dim)),Image.Resampling.NEAREST)
    if fmt == 'pdf':
        pdf = canvas.Canvas(out,pagesize=(360,420 if frame else 360))
        pdf.drawImage(ImageReader(image),18,18,width=324,height=(384 if frame else 324),preserveAspectRatio=True,anchor='c')
        pdf.setTitle('TuraQRcode')
        pdf.showPage(); pdf.save()
        return out.getvalue(),'application/pdf'
    image.save(out,'PNG')
    return out.getvalue(),'image/png'
