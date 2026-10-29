"""Standards-based linear barcodes, with consistent PNG/SVG/PDF exports."""
import io
import re
import barcode
from barcode.writer import ImageWriter, SVGWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

FORMATS={'code128':'code128','code39':'code39','ean13':'ean13','ean8':'ean8','upca':'upca'}


def symbol(content,writer=None):
    cls=barcode.get_barcode_class(FORMATS[content['format']])
    return cls(content['value'],writer=writer,**({'add_checksum':False} if content['format']=='code39' else {}))


def validate_barcode(content):
    if set(content)-{'format','value','show_text'}: raise ValueError('Unsupported barcode options.')
    fmt=content.get('format','code128'); value=content.get('value','')
    if fmt not in FORMATS or not isinstance(value,str): raise ValueError('Choose a supported barcode format and enter its value.')
    if not isinstance(content.get('show_text',True),bool): raise ValueError('Choose whether to display the barcode value.')
    if not value or len(value)>80: raise ValueError('Enter a barcode value of 1–80 characters.')
    if fmt=='code128' and any(ord(c)<32 or ord(c)>126 for c in value):
        raise ValueError('Code 128 supports printable English letters, numbers, and punctuation.')
    if fmt=='code39' and not re.fullmatch(r'[A-Z0-9 .$/+%\-]+',value):
        raise ValueError('Code 39 supports uppercase letters, numbers, spaces, and - . $ / + %.')
    if fmt in ('ean13','ean8','upca'):
        length={'ean13':13,'ean8':8,'upca':12}[fmt]
        if not value.isascii() or not value.isdigit() or len(value) not in (length-1,length):
            raise ValueError(f'Enter {length-1} digits, or {length} digits including the check digit.')
        generated=symbol({'format':fmt,'value':value[:-1] if len(value)==length else value}).get_fullcode()
        if len(value)==length and value!=generated: raise ValueError('The barcode check digit is incorrect.')
        value=generated
    return {'format':fmt,'value':value,'show_text':content.get('show_text',True)}


def render_barcode(content,design,fmt='png',size=1024):
    options={'module_width':.3,'module_height':22,'quiet_zone':6.5,'font_size':11,
             'write_text':content.get('show_text',True),'foreground':design.get('foreground','#163b75'),
             'background':design.get('background','#ffffff'),'dpi':300}
    out=io.BytesIO()
    symbol(content,SVGWriter() if fmt=='svg' else ImageWriter()).write(out,options)
    if fmt=='svg': return out.getvalue(),'image/svg+xml'
    image=Image.open(io.BytesIO(out.getvalue())).convert('RGB')
    # Never reduce narrow bars below two pixels; a long Code 128 can exceed size.
    width=max(size,image.width)
    image=image.resize((width,round(width*image.height/image.width)),Image.Resampling.NEAREST)
    out=io.BytesIO()
    if fmt=='pdf':
        pdf=canvas.Canvas(out,pagesize=(600,260)); pdf.setTitle('TuraQRcode barcode')
        pdf.drawImage(ImageReader(image),24,24,width=552,height=212,preserveAspectRatio=True,anchor='c')
        pdf.showPage();pdf.save()
        return out.getvalue(),'application/pdf'
    image.save(out,'PNG')
    return out.getvalue(),'image/png'
