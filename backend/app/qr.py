import base64
import io
import math
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
            img.thumbnail((1024,1024),Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.convert('RGBA').save(out, 'PNG')
        return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValueError('Upload a PNG, JPG, or WebP logo smaller than 500 KB and 4 megapixels.')


def vescape(s):
    return str(s).replace('\\','\\\\').replace('\r','').replace('\n',r'\n').replace(';',r'\;').replace(',',r'\,')


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


def _gradient_image(start,end,angle,width,height):
    mask=Image.linear_gradient('L').rotate(90-angle, resample=Image.Resampling.BICUBIC).resize((width,height),Image.Resampling.BICUBIC)
    return ImageOps.colorize(mask,start,end)


def render(data, design, fmt='png', size=1024,print_width_cm=None,print_preset='standard'):
    m = qr_matrix(data)
    n = len(m)
    cell = 12
    dim = n * cell
    frame = design.get('frame','none') in ('scan','banner')
    top_text, bottom_text = design.get('top_text',''), design.get('bottom_text','')
    top_offset=max(-8,min(32,int(design.get('top_text_offset',0))))
    bottom_offset=max(-8,min(32,int(design.get('bottom_text_offset',0))))
    top_height = 40+max(0,top_offset) if top_text else 0
    bottom_text_height = 40+max(0,bottom_offset) if bottom_text else 0
    frame_height = 64 if frame else 0
    code_top = top_height
    height = top_height + dim + frame_height + bottom_text_height
    fg, bg = design.get('foreground','#163b75'), design.get('background','#ffffff')
    bg_end = design.get('background_end')
    bg_fill = 'url(#qr-background)' if bg_end else bg
    fg_end = design.get('foreground_end')
    fg_fill = 'url(#qr-foreground)' if fg_end else fg
    angle = int(design.get('background_angle',0))
    fg_angle = int(design.get('foreground_angle',0))
    defs=[]
    if bg_end:
        radians=math.radians(angle)
        defs.append(f'<linearGradient id="qr-background" x1="{50-50*math.cos(radians):.2f}%" y1="{50-50*math.sin(radians):.2f}%" x2="{50+50*math.cos(radians):.2f}%" y2="{50+50*math.sin(radians):.2f}%"><stop offset="0%" stop-color="{bg}"/><stop offset="100%" stop-color="{bg_end}"/></linearGradient>')
    if fg_end:
        radians=math.radians(fg_angle)
        defs.append(f'<linearGradient id="qr-foreground" x1="{50-50*math.cos(radians):.2f}%" y1="{50-50*math.sin(radians):.2f}%" x2="{50+50*math.cos(radians):.2f}%" y2="{50+50*math.sin(radians):.2f}%"><stop offset="0%" stop-color="{fg}"/><stop offset="100%" stop-color="{fg_end}"/></linearGradient>')
    gradient_def=f'<defs>{"".join(defs)}</defs>' if defs else ''
    pattern = design.get('pattern','square')
    logo = design.get('logo')
    legacy_eye_style=design.get('eye_style','square')
    eye_frame_style=design.get('eye_frame_style') or legacy_eye_style
    eye_ball_style=design.get('eye_ball_style') or legacy_eye_style
    eye_color=design.get('eye_color') or fg
    eye_fill=fg_fill if not design.get('eye_color') else eye_color
    text_size=max(12,min(36,int(design.get('text_size',20))))
    text_bold=bool(design.get('text_bold',True))
    text_italic=bool(design.get('text_italic',False))

    def label_style(position):
        return {
            'size': max(12,min(36,int(design.get(position+'_text_size') or text_size))),
            'bold': text_bold if design.get(position+'_text_bold') is None else bool(design.get(position+'_text_bold')),
            'italic': text_italic if design.get(position+'_text_italic') is None else bool(design.get(position+'_text_italic')),
            'color': design.get(position+'_text_color') or fg,
        }

    def font_family(bold,italic):
        if bold and italic:
            return ('DejaVuSans-BoldOblique.ttf','Arialbi.ttf','Arial Bold Italic.ttf')
        if bold:
            return ('DejaVuSans-Bold.ttf','arialbd.ttf','Arial Bold.ttf')
        if italic:
            return ('DejaVuSans-Oblique.ttf','ariali.ttf','Arial Italic.ttf')
        return ('DejaVuSans.ttf','arial.ttf','Arial.ttf')

    def label_font(label,style):
        font_size=style['size']
        for candidate in font_family(style['bold'],style['italic']):
            try:
                font=ImageFont.truetype(candidate,font_size)
                while draw.textbbox((0,0),label,font=font)[2] > dim-32 and font_size > 8:
                    font_size-=1
                    font=ImageFont.truetype(candidate,font_size)
                return font
            except OSError:
                continue
        return ImageFont.load_default(size=font_size)

    def svg_shape(x,y,edge,style,color):
        if style == 'circle':
            return f'<circle cx="{x+edge/2:g}" cy="{y+edge/2:g}" r="{edge/2:g}" fill="{color}"/>'
        if style == 'diamond':
            return f'<polygon points="{x+edge/2:g},{y:g} {x+edge:g},{y+edge/2:g} {x+edge/2:g},{y+edge:g} {x:g},{y+edge/2:g}" fill="{color}"/>'
        radius=edge*.2 if style=='rounded' else 0
        return f'<rect x="{x:g}" y="{y:g}" width="{edge:g}" height="{edge:g}" rx="{radius:g}" fill="{color}"/>'

    def raster_shape(x,y,edge,style,color):
        if style == 'circle':
            draw.ellipse((x,y,x+edge-1,y+edge-1),fill=color)
        elif style == 'diamond':
            draw.polygon(((x+edge/2,y),(x+edge,y+edge/2),(x+edge/2,y+edge),(x,y+edge/2)),fill=color)
        else:
            radius=int(edge*.2) if style=='rounded' else 0
            draw.rounded_rectangle((x,y,x+edge-1,y+edge-1),radius=radius,fill=color)

    def label_svg(label,y,style):
        weight='700' if style['bold'] else '400'
        italic='italic' if style['italic'] else 'normal'
        estimate=len(label)*style['size']*.65
        fit=f' textLength="{dim-32}" lengthAdjust="spacingAndGlyphs"' if estimate > dim-32 else ''
        return f'<text x="{dim//2}" y="{y}" text-anchor="middle" font-family="Arial,sans-serif" font-weight="{weight}" font-style="{italic}" font-size="{style["size"]}" fill="{style["color"]}"{fit}>{escape(label)}</text>'

    def draw_label(label,y,style):
        draw.text((dim//2,y),label,fill=style['color'],anchor='mm',font=label_font(label,style))

    def finder(x,y):
        return (4 <= x < 11 and 4 <= y < 11) or (n-11 <= x < n-4 and 4 <= y < 11) or (4 <= x < 11 and n-11 <= y < n-4)

    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{round(size*height/dim)}" viewBox="0 0 {dim} {height}">', gradient_def, f'<rect width="100%" height="100%" fill="{bg_fill}"/>']
    if bg_end:
        image=_gradient_image(bg,bg_end,angle,dim,height)
    else:
        image = Image.new('RGB',(dim,height),bg)
    background_image=image.copy()
    draw = ImageDraw.Draw(image)
    ink_mask=Image.new('L',(dim,height),0)
    mask_draw=ImageDraw.Draw(ink_mask)
    for y,row in enumerate(m):
        for x,on in enumerate(row):
            if not on or (finder(x,y) and (eye_frame_style!='square' or eye_ball_style!='square' or eye_color!=fg)): continue
            px,py = x*cell,code_top+y*cell
            # Timing/alignment structures remain full modules. Styling data
            # modules preserves the four-module quiet zone around the symbol.
            functional=finder(x,y) or x==10 or y==10
            if pattern == 'dots' and not functional:
                elements.append(f'<circle cx="{px+6}" cy="{py+6}" r="5.8" fill="{fg_fill}"/>')
                draw.ellipse((px,py,px+11,py+11),fill=fg)
                mask_draw.ellipse((px,py,px+11,py+11),fill=255)
            elif pattern=='diamond' and not functional:
                points=[(px+6,py),(px+12,py+6),(px+6,py+12),(px,py+6)]
                elements.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in points)+f'" fill="{fg_fill}"/>')
                draw.polygon(points,fill=fg)
                mask_draw.polygon(points,fill=255)
            else:
                rad = (5 if pattern=='soft' else 3) if pattern in ('rounded','soft') and not functional else 0
                dx=1 if pattern=='vertical' and not functional else 0
                dy=1 if pattern=='horizontal' and not functional else 0
                elements.append(f'<rect x="{px+dx}" y="{py+dy}" width="{12-2*dx}" height="{12-2*dy}" rx="{rad}" fill="{fg_fill}"/>')
                draw.rounded_rectangle((px+dx,py+dy,px+11-dx,py+11-dy),radius=rad,fill=fg)
                mask_draw.rounded_rectangle((px+dx,py+dy,px+11-dx,py+11-dy),radius=rad,fill=255)
    if eye_frame_style!='square' or eye_ball_style!='square' or eye_color!=fg:
        for ex,ey in ((4,4),(n-11,4),(4,n-11)):
            px,py=ex*cell,code_top+ey*cell
            outer,inner=7*cell,5*cell
            elements.append(svg_shape(px,py,outer,eye_frame_style,eye_fill))
            elements.append(svg_shape(px+cell,py+cell,inner,eye_frame_style,bg_fill))
            elements.append(svg_shape(px+2*cell,py+2*cell,3*cell,eye_ball_style,eye_fill))
            raster_shape(px,py,outer,eye_frame_style,eye_color)
            mask_draw.rectangle((px,py,px+outer-1,py+outer-1),fill=255)
            if bg_end:
                image.paste(background_image.crop((px+cell,py+cell,px+cell+inner,py+cell+inner)),(px+cell,py+cell))
            else:
                raster_shape(px+cell,py+cell,inner,eye_frame_style,bg)
            mask_draw.rectangle((px+cell,py+cell,px+cell+inner-1,py+cell+inner-1),fill=0)
            raster_shape(px+2*cell,py+2*cell,3*cell,eye_ball_style,eye_color)
            mask_draw.rectangle((px+2*cell,py+2*cell,px+5*cell-1,py+5*cell-1),fill=255)
    if fg_end:
        qr_ink=_gradient_image(fg,fg_end,fg_angle,dim,dim)
        image.paste(qr_ink,(0,code_top),ink_mask.crop((0,code_top,dim,code_top+dim)))
    if logo:
        edge = int(dim*.15)
        x,y = (dim-edge)//2,code_top+(dim-edge)//2
        elements.append(f'<rect x="{x-7}" y="{y-7}" width="{edge+14}" height="{edge+14}" rx="8" fill="#ffffff"/>')
        elements.append(f'<image href="{escape(logo,quote=True)}" x="{x}" y="{y}" width="{edge}" height="{edge}" preserveAspectRatio="xMidYMid meet"/>')
    if top_text:
        style=label_style('top')
        top_center=20+max(0,-top_offset)
        elements.append(label_svg(top_text,top_center+style['size']//3,style))
        draw_label(top_text,top_center,style)
    if frame:
        label=design.get('frame_label','SCAN ME')
        label_color=fg if design.get('frame')=='banner' else bg
        fill=bg if design.get('frame')=='banner' else fg
        frame_y=code_top+dim
        frame_font_size=max(10,min(20,int((dim-40)/max(1,len(label)*.62))))
        elements.extend([f'<rect x="12" y="{frame_y}" width="{dim-24}" height="52" rx="10" fill="{fill}" stroke="{fg}" stroke-width="2"/>',f'<text x="{dim//2}" y="{frame_y+26+frame_font_size*.35:g}" text-anchor="middle" font-family="Arial,sans-serif" font-weight="700" font-size="{frame_font_size}" fill="{label_color}">{escape(label)}</text>'])
        draw.rounded_rectangle((12,frame_y,dim-12,frame_y+52),radius=10,fill=fill,outline=fg,width=2)
        draw.text((dim//2,frame_y+26),label,fill=label_color,anchor='mm',font=ImageFont.load_default(size=frame_font_size))
    if bottom_text:
        style=label_style('bottom')
        label_y=code_top+dim+frame_height+20+bottom_offset
        elements.append(label_svg(bottom_text,label_y+style['size']//3,style))
        draw_label(bottom_text,label_y,style)
    if design.get('frame')=='border':
        # Draw the border outside the complete four-module quiet zone.
        elements[0]=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{round(size*(height+32)/(dim+32))}" viewBox="-16 -16 {dim+32} {height+32}">'
        elements[2]=f'<rect x="-16" y="-16" width="{dim+32}" height="{height+32}" fill="{bg_fill}"/>'
        elements.append(f'<rect x="-13" y="-13" width="{dim+26}" height="{height+26}" rx="18" fill="none" stroke="{fg}" stroke-width="4"/>')
        image=ImageOps.expand(image,border=16,fill=bg)
        ImageDraw.Draw(image).rounded_rectangle((3,3,dim+28,height+28),radius=18,outline=fg,width=4)
    elements.append('</svg>')
    if fmt == 'svg': return ''.join(elements).encode(), 'image/svg+xml'
    out = io.BytesIO()
    border=design.get('frame')=='border'
    image_width=dim+32 if border else dim
    image_height=height+32 if border else height
    image = image.resize((size,round(size*image_height/image_width)),Image.Resampling.NEAREST)
    if logo:
        qr_width=round(dim*size/image_width)
        qr_left=round((size-qr_width)/2)
        qr_top=round((code_top+(16 if border else 0))*size/image_width)
        logo_edge=max(8,round(qr_width*.15))
        padding=max(4,round(logo_edge*.10))
        left=qr_left+(qr_width-logo_edge)//2
        top=qr_top+(qr_width-logo_edge)//2
        final_draw=ImageDraw.Draw(image)
        final_draw.rounded_rectangle((left-padding,top-padding,left+logo_edge+padding,top+logo_edge+padding),radius=max(4,round(padding*.8)),fill='#ffffff')
        with Image.open(io.BytesIO(base64.b64decode(logo.split(',',1)[1]))) as mark:
            mark=mark.convert('RGBA')
            mark.thumbnail((logo_edge,logo_edge),Image.Resampling.LANCZOS)
            image.alpha_composite(mark,(left+(logo_edge-mark.width)//2,top+(logo_edge-mark.height)//2)) if image.mode=='RGBA' else image.paste(mark,(left+(logo_edge-mark.width)//2,top+(logo_edge-mark.height)//2),mark)
    if fmt == 'pdf':
        if print_preset=='business_card':
            page_width,page_height=90*72/25.4,50*72/25.4
            max_width,max_height=34*72/25.4,34*72/25.4
        elif print_preset=='a4':
            page_width,page_height=210*72/25.4,297*72/25.4
            max_width,max_height=170*72/25.4,230*72/25.4
        else:
            page_width=(print_width_cm*72/2.54) if print_width_cm else (size*72/300)
            page_height=page_width*image_height/image_width
            max_width,max_height=page_width,page_height
        scale=min(max_width/image_width,max_height/image_height)
        draw_width,draw_height=image_width*scale,image_height*scale
        pdf = canvas.Canvas(out,pagesize=(page_width,page_height))
        pdf.drawImage(ImageReader(image),(page_width-draw_width)/2,(page_height-draw_height)/2,width=draw_width,height=draw_height,preserveAspectRatio=True,anchor='c')
        pdf.setTitle('TuraQRcode')
        pdf.showPage(); pdf.save()
        return out.getvalue(),'application/pdf'
    image.save(out,'PNG')
    return out.getvalue(),'image/png'
