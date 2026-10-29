import {useEffect,useMemo,useState,type FormEvent} from 'react';
import {useNavigate} from 'react-router-dom';
import {Barcode,Download,ArrowRight,ScanLine,SlidersHorizontal} from 'lucide-react';
import {API,api,post,patch,message,saveBlob,download} from '../shared/api';
import {Button,Field,ErrorBox,Success} from '../shared/ui';
import type {Code,Design,Project} from '../shared/types';
import DesignColors from './DesignColors';

const formats=[
 {id:'code128',label:'Code 128',hint:'Letters, numbers, and punctuation. Ideal for labels, inventory, and tracked website destinations.',sample:'TURA-2026-001'},
 {id:'ean13',label:'EAN-13',hint:'12 digits, or 13 including a valid check digit. Common on retail products.',sample:'590123412345'},
 {id:'ean8',label:'EAN-8',hint:'7 digits, or 8 including a valid check digit. Compact retail labels.',sample:'9638507'},
 {id:'upca',label:'UPC-A',hint:'11 digits, or 12 including a valid check digit. Common in North America.',sample:'03600029145'},
 {id:'code39',label:'Code 39',hint:'Uppercase letters, numbers, spaces, and - . $ / + %.',sample:'TURA-001'},
];
const initialDesign:Design={foreground:'#163b75',background:'#ffffff',pattern:'square',frame:'none',logo:null,barcode_module_width:0.3,barcode_height:22,barcode_font_size:11};

export default function BarcodeBuilder({guest=false,initial,onSaved}:{guest?:boolean;initial?:Code;onSaved?:(c:Code)=>void}){
 const navigate=useNavigate();
 const [format,setFormat]=useState(String(initial?.content.format||'code128'));
 const [value,setValue]=useState(String(initial?.content.value||''));
 const [showText,setShowText]=useState(initial?.content.show_text!==false);
 const [tracked,setTracked]=useState(initial?.mode==='dynamic');
 const [name,setName]=useState(initial?.name||'');
 const [project,setProject]=useState(initial?.project_id||'');
 const [projects,setProjects]=useState<Project[]>([]);
 const [design,setDesign]=useState<Design>(initial?.design||initialDesign);
 const [preview,setPreview]=useState('');
 const [previewError,setPreviewError]=useState('');
 const [error,setError]=useState('');
 const [success,setSuccess]=useState('');
 const [busy,setBusy]=useState(false);
 const [exportFormat,setExportFormat]=useState('png');
 const selected=useMemo(()=>formats.find(f=>f.id===format)!,[format]);
 const content={format,value,show_text:showText,tracked:tracked&&!guest};

 useEffect(()=>{if(!guest)api<Project[]>('/api/projects').then(setProjects).catch(()=>{});},[guest]);
 useEffect(()=>{
  let objectUrl='';const controller=new AbortController();setPreview('');setPreviewError('');
  const timer=setTimeout(async()=>{
   if(!value)return;
   try{
    const previewContent=initial?.mode==='dynamic'&&initial.qr_payload?{...content,value:initial.qr_payload,tracked:false}:content;
    const r=await fetch(API+'/api/qr/preview?format=svg',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'barcode',content:previewContent,design}),signal:controller.signal});
    if(!r.ok){const body=await r.json();throw new Error(body.detail||'Please check the barcode details.');}
    objectUrl=URL.createObjectURL(await r.blob());setPreview(objectUrl);
   }catch(e){if(!controller.signal.aborted)setPreviewError(message(e));}
  },300);
  return()=>{clearTimeout(timer);controller.abort();if(objectUrl)URL.revokeObjectURL(objectUrl);};
 },[format,value,showText,tracked,initial?.mode,initial?.qr_payload,JSON.stringify(design)]);

 async function downloadBarcode(){
  setBusy(true);setError('');
  try{
   if(initial)await download('/api/codes/'+initial.id+'/download?format='+exportFormat,(name||'tura-barcode')+'.'+exportFormat);
   else{
    const r=await fetch(API+'/api/qr/preview?format='+exportFormat,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'barcode',content,design})});
    if(!r.ok){const body=await r.json();throw new Error(body.detail||'Your download could not be completed.');}
    saveBlob(await r.blob(),(name||'tura-barcode')+'.'+exportFormat);
   }
  }catch(e){setError(message(e));}finally{setBusy(false);}
 }

 async function save(e:FormEvent){
  e.preventDefault();setBusy(true);setError('');setSuccess('');
  try{
   const patchData={name,design,project_id:project||null,content};
   const code=initial
    ?await patch<Code>('/api/codes/'+initial.id,patchData)
    :await post<Code>('/api/codes',{name,kind:'barcode',mode:tracked?'dynamic':'static',content,design,project_id:project||null});
   if(onSaved){onSaved(code);setSuccess('Your barcode settings have been saved.');}
   else navigate('/app/codes/'+code.id,{state:{created:true}});
  }catch(e){setError(message(e));}finally{setBusy(false);}
 }

 return <form className="builder barcode-builder" onSubmit={save}>
  <section className="builder-editor">
   <div className="builder-body">
    <div className="builder-section-head"><h2>{initial?'Barcode details':'Create a barcode'}</h2><p>Choose a barcode standard, enter its value, and shape a print-ready design.</p></div>
    {!guest&&<Field label="Barcode name"><input value={name} onChange={e=>setName(e.target.value)} maxLength={120} required placeholder="e.g. Product label"/></Field>}
    <Field label="Barcode format"><select value={format} disabled={Boolean(initial)} onChange={e=>{setFormat(e.target.value);setValue('');setTracked(false);}}>{formats.map(f=><option value={f.id} key={f.id}>{f.label}</option>)}</select></Field>
    <Field label={tracked?'Website destination':'Barcode value'} hint={selected.hint}><input type={tracked?'url':'text'} value={value} onChange={e=>setValue(e.target.value)} placeholder={tracked?'https://example.com/product':selected.sample} maxLength={tracked?2048:80} required disabled={Boolean(initial&&initial.mode==='static')} spellCheck={false}/></Field>
    {!guest&&format==='code128'&&!initial&&<div className="tracking-option"><label className="checkbox-label"><input type="checkbox" checked={tracked} onChange={e=>setTracked(e.target.checked)}/><span><strong>Measure scans with a managed link</strong><small>Code 128 scanners open your website destination through TuraQRcode so visits can be counted.</small></span></label></div>}
    {!guest&&initial?.mode==='dynamic'&&<div className="notice info"><ScanLine size={16}/> Tracked Code 128 is active. Scans through the barcode link appear in Analytics.</div>}
    <label className="checkbox-label"><input type="checkbox" checked={showText} onChange={e=>setShowText(e.target.checked)}/>Show value below barcode</label>
    <div className="design-divider"/>
    <section className="barcode-design-controls">
     <div className="qr-design-label"><span className="qr-design-icon"><SlidersHorizontal size={16}/></span><div><h3>Barcode appearance</h3><p>Use a clear, high-contrast palette and adjust the printed proportions.</p></div></div>
     <DesignColors design={design} onChange={setDesign} label="Bar color" showEyes={false} heading="Barcode colors"/>
     <div className="barcode-size-controls">
      <Field label="Bar height"><div className="qr-size-control"><input aria-label="Bar height" type="range" min="12" max="60" step="1" value={design.barcode_height??22} onChange={e=>setDesign({...design,barcode_height:Number(e.target.value)})}/><output>{design.barcode_height??22} mm</output></div></Field>
      <Field label="Bar width"><div className="qr-size-control"><input aria-label="Bar width" type="range" min="0.2" max="0.8" step="0.05" value={design.barcode_module_width??0.3} onChange={e=>setDesign({...design,barcode_module_width:Number(e.target.value)})}/><output>{(design.barcode_module_width??0.3).toFixed(2)} mm</output></div></Field>
      {showText&&<Field label="Printed value size"><div className="qr-size-control"><input aria-label="Printed value size" type="range" min="8" max="24" step="1" value={design.barcode_font_size??11} onChange={e=>setDesign({...design,barcode_font_size:Number(e.target.value)})}/><output>{design.barcode_font_size??11} pt</output></div></Field>}
     </div>
    </section>
    {!guest&&<Field label="Project"><select value={project} onChange={e=>setProject(e.target.value)}><option value="">Default project</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>}
    <p className="sublabel">Retail identifiers must come from the appropriate issuing organization. Keep the quiet space around the bars when printing.</p>
    <ErrorBox error={error}/>{success&&<Success>{success}</Success>}
   </div>
   {!guest&&<div className="builder-footer"><span>Saved barcodes remain available in Barcode history</span><Button type="submit" busy={busy} disabled={!preview||Boolean(previewError)}>{initial?'Save changes':'Save barcode'}<ArrowRight size={16}/></Button></div>}
  </section>
  <aside className="builder-preview">
   <div className="preview-label"><span>YOUR BARCODE</span><span className="badge">{selected.label}</span></div>
   <div className="barcode-stage">{preview?<img src={preview} alt="Your barcode preview"/>:<Barcode size={130} strokeWidth={1}/>}</div>
   <ErrorBox error={previewError}/>
   <p className="preview-description">{tracked?'The saved Code 128 will point to your managed link and record scan requests.':'Keep the clear space around the bars when placing your label.'}</p>
   <div className="download-options"><Field label="Download format"><select value={exportFormat} onChange={e=>setExportFormat(e.target.value)}><option value="png">PNG · Image</option><option value="svg">SVG · Vector</option><option value="pdf">PDF · Print</option></select></Field><Button type="button" className="full" busy={busy} disabled={!preview||Boolean(previewError)||(tracked&&!initial&&!guest)} onClick={downloadBarcode}><Download size={16}/>Download {exportFormat.toUpperCase()}</Button>{tracked&&!initial&&!guest&&<p className="sublabel">Save the barcode first to download its unique tracked link.</p>}</div>
  </aside>
 </form>;
}
