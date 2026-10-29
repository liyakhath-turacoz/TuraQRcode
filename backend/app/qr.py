import base64
import io
from html import escape
from urllib.parse import quote, urlencode
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
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
    if kind == 'barcode': return c['value']
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


def render_code(kind,content,design,fmt='png',size=1024,data=None):
    if kind=='barcode':
        from .barcodes import render_barcode
        return render_barcode(content,design,fmt,size)
    return render(data if data is not None else payload(kind,content),design,fmt,size)


def render(data, design, fmt='png', size=1024):
    m = qr_matrix(data)
    n = len(m)
    cell = 12
    dim = n * cell
    frame = design.get('frame','none') in ('scan','banner')
    height = dim + (64 if frame else 0)
    fg, bg = design.get('foreground','#163b75'), design.get('background','#ffffff')
    pattern = design.get('pattern','square')
    logo = design.get('logo')
    eye_style=design.get('eye_style','square')
    eye_color=design.get('eye_color') or fg

    def finder(x,y):
        return (4 <= x < 11 and 4 <= y < 11) or (n-11 <= x < n-4 and 4 <= y < 11) or (4 <= x < 11 and n-11 <= y < n-4)

    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{round(size*height/dim)}" viewBox="0 0 {dim} {height}">', f'<rect width="100%" height="100%" fill="{bg}"/>']
    image = Image.new('RGB',(dim,height),bg)
    draw = ImageDraw.Draw(image)
    for y,row in enumerate(m):
        for x,on in enumerate(row):
            if not on or (finder(x,y) and (eye_style!='square' or eye_color!=fg)): continue
            px,py = x*cell,y*cell
            # Timing/alignment structures remain full modules. Styling data
            # modules preserves the four-module quiet zone around the symbol.
            functional=finder(x,y) or x==10 or y==10
            if pattern == 'dots' and not functional:
                elements.append(f'<circle cx="{px+6}" cy="{py+6}" r="5.8" fill="{fg}"/>')
                draw.ellipse((px,py,px+11,py+11),fill=fg)
            elif pattern=='diamond' and not functional:
                points=[(px+6,py),(px+12,py+6),(px+6,py+12),(px,py+6)]
                elements.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in points)+f'" fill="{fg}"/>')
                draw.polygon(points,fill=fg)
            else:
                rad = (5 if pattern=='soft' else 3) if pattern in ('rounded','soft') and not functional else 0
                dx=1 if pattern=='vertical' and not functional else 0
                dy=1 if pattern=='horizontal' and not functional else 0
                elements.append(f'<rect x="{px+dx}" y="{py+dy}" width="{12-2*dx}" height="{12-2*dy}" rx="{rad}" fill="{fg}"/>')
                draw.rounded_rectangle((px+dx,py+dy,px+11-dx,py+11-dy),radius=rad,fill=fg)
    if eye_style!='square' or eye_color!=fg:
        for ex,ey in ((4,4),(n-11,4),(4,n-11)):
            for inset,color in ((0,eye_color),(1,bg),(2,eye_color)):
                edge=(7-2*inset)*cell; px=(ex+inset)*cell;py=(ey+inset)*cell
                radius=edge/2 if eye_style=='circle' else (14 if eye_style=='rounded' else 0)
                elements.append(f'<rect x="{px}" y="{py}" width="{edge}" height="{edge}" rx="{radius}" fill="{color}"/>')
                draw.rounded_rectangle((px,py,px+edge-1,py+edge-1),radius=radius,fill=color)
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
        label=design.get('frame_label','SCAN ME')
        label_color=fg if design.get('frame')=='banner' else bg
        fill=bg if design.get('frame')=='banner' else fg
        elements.extend([f'<rect x="12" y="{dim}" width="{dim-24}" height="52" rx="10" fill="{fill}" stroke="{fg}" stroke-width="2"/>',f'<text x="{dim//2}" y="{dim+33}" text-anchor="middle" font-family="Arial,sans-serif" font-weight="700" font-size="20" fill="{label_color}">{escape(label)}</text>'])
        draw.rounded_rectangle((12,dim,dim-12,dim+52),radius=10,fill=fill,outline=fg,width=2)
        draw.text((dim//2,dim+26),label,fill=label_color,anchor='mm',font=ImageFont.load_default(size=20))
    if design.get('frame')=='border':
        # Draw the border outside the complete four-module quiet zone.
        elements[0]=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="-16 -16 {dim+32} {dim+32}">'
        elements[1]=f'<rect x="-16" y="-16" width="{dim+32}" height="{dim+32}" fill="{bg}"/>'
        elements.append(f'<rect x="-13" y="-13" width="{dim+26}" height="{dim+26}" rx="18" fill="none" stroke="{fg}" stroke-width="4"/>')
        image=ImageOps.expand(image,border=16,fill=bg)
        ImageDraw.Draw(image).rounded_rectangle((3,3,dim+28,dim+28),radius=18,outline=fg,width=4)
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
