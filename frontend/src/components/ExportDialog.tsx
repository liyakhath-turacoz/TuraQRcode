import {useState} from 'react';
import {Download,FileImage,FileText} from 'lucide-react';
import {Button,ErrorBox,Field,Modal} from '../shared/ui';
import {message} from '../shared/api';

export type ExportFormat='png'|'svg'|'pdf';
export type ExportSize='standard'|'social'|'business_card'|'a4'|'high_res';
export type ExportOptions={format:ExportFormat;widthPx:number;size:ExportSize};
const sizes:{id:ExportSize;label:string;width:number;detail:string}[]=[
 {id:'standard',label:'Standard share',width:1024,detail:'1,024 px square · everyday use'},
 {id:'social',label:'Social post',width:1080,detail:'1,080 px square · social profiles'},
 {id:'business_card',label:'Business card',width:1200,detail:'1,200 px · 90 × 50 mm PDF layout'},
 {id:'a4',label:'A4 print sheet',width:2400,detail:'2,400 px · A4 PDF with centered code'},
 {id:'high_res',label:'High resolution',width:3000,detail:'3,000 px square · large format'},
];

export default function ExportDialog({onClose,onExport,title='Download QR code'}:{onClose:()=>void;onExport:(options:ExportOptions)=>Promise<void>;title?:string}){
 const [format,setFormat]=useState<ExportFormat>('png');
 const [size,setSize]=useState<ExportSize>('standard');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const selectedSize=sizes.find(item=>item.id===size)!;
 async function submit(){setBusy(true);setError('');try{await onExport({format,widthPx:selectedSize.width,size});onClose();}catch(exception){setError(message(exception));}finally{setBusy(false);}}
 return <Modal title={title} onClose={onClose}>
  <div className="export-dialog-copy"><span><FileImage size={17}/></span><p>Choose a file type and output size. Your design, clear margin, labels, and logo are included.</p></div>
  <Field label="File format"><select value={format} onChange={event=>setFormat(event.target.value as ExportFormat)}><option value="png">PNG · Image</option><option value="svg">SVG · Scalable vector</option><option value="pdf">PDF · Print ready</option></select></Field>
  <Field label="Output size"><select value={size} onChange={event=>setSize(event.target.value as ExportSize)}>{sizes.map(item=><option key={item.id} value={item.id}>{item.label} · {item.detail}</option>)}</select></Field>
  <p className="export-dpi-note"><FileText size={15}/> {selectedSize.width.toLocaleString()} px · {selectedSize.detail}</p>
  <ErrorBox error={error}/>
  <div className="modal-actions"><Button type="button" className="secondary" onClick={onClose}>Cancel</Button><Button type="button" busy={busy} onClick={submit}><Download size={16}/>Download {format.toUpperCase()}</Button></div>
 </Modal>;
}
