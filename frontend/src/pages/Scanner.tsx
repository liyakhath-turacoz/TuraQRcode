import {useEffect,useRef,useState,type ChangeEvent} from 'react';
import {Barcode,Camera,Check,Copy,ExternalLink,ImageUp,ScanLine,ShieldCheck,Square,X} from 'lucide-react';
import {BarcodeFormat,DecodeHintType} from '@zxing/library';
import {BrowserMultiFormatReader,type IScannerControls} from '@zxing/browser';
import {Button,ErrorBox,Field,PageHeader} from '../shared/ui';
import './scanner.css';

type ScanResult={text:string;format:string;url:string|null};
type State='idle'|'starting'|'scanning'|'reading';
const imageTypes=new Set(['image/png','image/jpeg','image/webp']);

class ScannerReader extends BrowserMultiFormatReader{
 constructor(){super(new Map<DecodeHintType,unknown>([[DecodeHintType.TRY_HARDER,true],[DecodeHintType.POSSIBLE_FORMATS,[BarcodeFormat.QR_CODE,BarcodeFormat.CODE_128,BarcodeFormat.CODE_39,BarcodeFormat.EAN_13,BarcodeFormat.EAN_8,BarcodeFormat.UPC_A,BarcodeFormat.UPC_E]]]),{delayBetweenScanAttempts:250});}
 override decodeFromCanvas(canvas:HTMLCanvasElement){
  try{return super.decodeFromCanvas(canvas);}catch{
   const context=canvas.getContext('2d',{willReadFrequently:true});if(!context)throw new Error('Image unavailable');
   const pixels=context.getImageData(0,0,canvas.width,canvas.height);
   for(let i=0;i<pixels.data.length;i+=4){pixels.data[i]=255-pixels.data[i];pixels.data[i+1]=255-pixels.data[i+1];pixels.data[i+2]=255-pixels.data[i+2];}
   context.putImageData(pixels,0,0);return super.decodeFromCanvas(canvas);
  }
 }
}

function webLink(text:string){
 const value=text.trim();
 if(!/^https?:\/\//i.test(value)||/[\u0000-\u001f\u007f]/.test(value))return null;
 try{const url=new URL(value);return url.hostname&&!url.username&&!url.password?url.href:null;}catch{return null;}
}

function cameraError(error:unknown){
 const name=error instanceof Error?error.name:'';
 if(name==='NotAllowedError'||name==='PermissionDeniedError')return 'Camera access was not allowed. Enable camera access in your browser settings and try again, or upload an image.';
 if(name==='NotFoundError'||name==='DevicesNotFoundError')return 'No camera was found. Connect a camera and try again, or upload an image.';
 if(name==='NotReadableError'||name==='TrackStartError')return 'Your camera is unavailable or in use by another application. Close the other application and try again, or upload an image.';
 if(name==='OverconstrainedError')return 'The selected camera is unavailable. Choose another camera or upload an image.';
 return 'The camera could not be started. Try again, or upload an image instead.';
}

export default function ScannerPage(){
 const [method,setMethod]=useState<'camera'|'image'>('camera');
 const [state,setState]=useState<State>('idle');
 const [result,setResult]=useState<ScanResult|null>(null);
 const [error,setError]=useState('');
 const [copied,setCopied]=useState(false);
 const [autoOpen,setAutoOpen]=useState(false);
 const [devices,setDevices]=useState<MediaDeviceInfo[]>([]);
 const [deviceId,setDeviceId]=useState('');
 const video=useRef<HTMLVideoElement>(null);
 const stream=useRef<MediaStream|null>(null);
 const controls=useRef<IScannerControls|null>(null);
 const operation=useRef(0);
 const mounted=useRef(true);
 const automatic=useRef(false);
 automatic.current=autoOpen;

 function release(){
  const current=controls.current;controls.current=null;
  try{current?.stop();}catch{/* Tracks are also released below. */}
  stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;
  if(video.current){video.current.pause();video.current.srcObject=null;}
 }
 function stop(){operation.current++;release();if(mounted.current)setState('idle');}
 function clear(){stop();setResult(null);setError('');setCopied(false);}
 function complete(text:string,format:BarcodeFormat){
  stop();const url=webLink(text);setResult({text,format:BarcodeFormat[format].replace(/_/g,' '),url});setCopied(false);setError('');
  if(url&&automatic.current)window.location.assign(url);
 }
 function reader(){return new ScannerReader();}

 useEffect(()=>{
  mounted.current=true;
  const hide=()=>{if(document.hidden)stop();};
  document.addEventListener('visibilitychange',hide);
  const leave=()=>stop();window.addEventListener('pagehide',leave);
  return()=>{mounted.current=false;operation.current++;release();document.removeEventListener('visibilitychange',hide);window.removeEventListener('pagehide',leave);};
 },[]);

 async function startCamera(selected=deviceId){
  clear();const token=operation.current;
  if(!window.isSecureContext){setError('Camera scanning needs a secure connection. Open this page using HTTPS, or upload an image.');return;}
  if(!navigator.mediaDevices?.getUserMedia){setError('Camera scanning is unavailable in this browser. Try a current browser, or upload an image.');return;}
  setState('starting');
  try{
   const capture=await navigator.mediaDevices.getUserMedia({audio:false,video:{...(selected?{deviceId:{exact:selected}}:{facingMode:{ideal:'environment'}}),width:{ideal:1280},height:{ideal:720}}});
   if(!mounted.current||token!==operation.current){capture.getTracks().forEach(track=>track.stop());return;}
   stream.current=capture;
   const active=await reader().decodeFromStream(capture,video.current!, (decoded,_error,activeControls)=>{
    if(!mounted.current||token!==operation.current){activeControls.stop();return;}
    if(decoded){activeControls.stop();complete(decoded.getText(),decoded.getBarcodeFormat());}
   });
   if(!mounted.current||token!==operation.current){active.stop();return;}
   controls.current=active;setState('scanning');
   const cameras=(await navigator.mediaDevices.enumerateDevices().catch(()=>[])).filter(device=>device.kind==='videoinput');
   if(mounted.current&&token===operation.current){setDevices(cameras);setDeviceId(capture.getVideoTracks()[0]?.getSettings().deviceId||selected);}
  }catch(exception){if(mounted.current&&token===operation.current){stop();setError(cameraError(exception));}}
 }

 async function readImage(event:ChangeEvent<HTMLInputElement>){
  const file=event.currentTarget.files?.[0];event.currentTarget.value='';if(!file)return;
  clear();const token=operation.current;
  if(!imageTypes.has(file.type)){setError('Choose a PNG, JPG, or WebP image.');return;}
  if(file.size>12*1024*1024){setError('Choose an image smaller than 12 MB.');return;}
  setState('reading');const objectURL=URL.createObjectURL(file);
  try{
   const image=new Image();image.src=objectURL;await image.decode();
   if(!mounted.current||token!==operation.current)return;
   if(!image.naturalWidth||image.naturalWidth>8000||image.naturalHeight>8000||image.naturalWidth*image.naturalHeight>24_000_000){setError('Choose an image up to 8,000 px per side and 24 megapixels.');return;}
   const canvas=document.createElement('canvas');const scale=Math.min(1,3200/Math.max(image.naturalWidth,image.naturalHeight));
   canvas.width=Math.round(image.naturalWidth*scale);canvas.height=Math.round(image.naturalHeight*scale);
   const context=canvas.getContext('2d',{willReadFrequently:true});if(!context)throw new Error('Image unavailable');
   context.fillStyle='#ffffff';context.fillRect(0,0,canvas.width,canvas.height);context.drawImage(image,0,0,canvas.width,canvas.height);
   const decoded=reader().decodeFromCanvas(canvas);
   if(mounted.current&&token===operation.current)complete(decoded.getText(),decoded.getBarcodeFormat());
  }catch{if(mounted.current&&token===operation.current)setError('No readable QR code or barcode was found. Try a sharper image with the entire code in view.');}
  finally{URL.revokeObjectURL(objectURL);if(mounted.current&&token===operation.current)setState('idle');}
 }

 const active=state==='starting'||state==='scanning';
 return <>
  <PageHeader title="QR Scanner" description="Scan a QR code or barcode to read its contents or open a web link."/>
  <div className="scanner-layout">
   <section className="panel scanner-input" aria-label="Scan a code">
    <div className="scanner-tabs" role="tablist" aria-label="Scanning method">
     {(['camera','image'] as const).map(value=><button key={value} type="button" id={'scan-tab-'+value} role="tab" aria-selected={method===value} aria-controls={'scan-panel-'+value} tabIndex={method===value?0:-1} onKeyDown={event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();clear();const next=event.key==='Home'?'camera':event.key==='End'?'image':value==='camera'?'image':'camera';setMethod(next);document.getElementById('scan-tab-'+next)?.focus();}}} onClick={()=>{if(method!==value){clear();setMethod(value);}}}>{value==='camera'?<Camera size={18}/>:<ImageUp size={18}/>} {value==='camera'?'Use camera':'Upload image'}</button>)}
    </div>
    <ErrorBox error={error}/>
    <div role="tabpanel" id="scan-panel-camera" aria-labelledby="scan-tab-camera" hidden={method!=='camera'}>
     <div className={'scanner-viewfinder'+(state==='scanning'?' is-active':'')}>
      <video ref={video} muted playsInline aria-label="Camera preview"/>
      {!active&&<div className="scanner-placeholder"><span><ScanLine size={45} strokeWidth={1.4}/></span><h2>Ready when you are</h2><p>Place the entire code in view, with good lighting and a steady camera.</p></div>}
      {state==='starting'&&<span className="scanner-starting">Waiting for camera access…</span>}
      {state==='scanning'&&<span className="scanner-camera-badge"><i/> Camera is on</span>}
     </div>
     {devices.length>1&&<Field label="Camera"><select value={deviceId} disabled={state==='starting'} onChange={event=>{const selected=event.target.value;setDeviceId(selected);if(active)void startCamera(selected);}}>{devices.map((device,index)=><option key={device.deviceId} value={device.deviceId}>{device.label||'Camera '+(index+1)}</option>)}</select></Field>}
     <div className="scanner-actions"><Button onClick={()=>void startCamera()} disabled={active}><Camera size={17}/>Start camera</Button>{active&&<Button className="secondary" onClick={stop}>{state==='starting'?<X size={16}/>:<Square size={16}/>} {state==='starting'?'Cancel':'Stop camera'}</Button>}</div>
    </div>
    <div role="tabpanel" id="scan-panel-image" aria-labelledby="scan-tab-image" hidden={method!=='image'}>
     <label className={'scanner-upload'+(state==='reading'?' is-reading':'')}><ImageUp size={37} strokeWidth={1.5}/><strong>{state==='reading'?'Reading your image…':'Choose an image to scan'}</strong><span>PNG, JPG, or WebP · Up to 12 MB</span><input type="file" aria-label="Image to scan" accept="image/png,image/jpeg,image/webp" disabled={state==='reading'} onChange={readImage}/></label>
     <p className="scanner-hint">Use a clear image showing one complete code. Up to 8,000 px per side and 24 megapixels.</p>
    </div>
    <label className="checkbox-label scanner-auto"><input type="checkbox" checked={autoOpen} onChange={event=>setAutoOpen(event.target.checked)}/><span>Open web links automatically<small>When enabled, a scanned web link opens in this tab.</small></span></label>
    <p className="scanner-privacy"><ShieldCheck size={16}/> Camera and image scans stay on your device. Opening a link visits its website.</p>
   </section>
   <section className="panel scanner-result" aria-label="Scan result" aria-live="polite" aria-atomic="true">
    {result?<>
     <div className="scanner-result-heading"><span className="scanner-success"><Check size={20}/></span><div><p className="eyebrow">SCAN COMPLETE</p><h2>{result.url?'Web link found':'Code contents'}</h2></div><span className="badge">{result.format}</span></div>
     <pre className="scanner-decoded" tabIndex={0} aria-label="Decoded content">{result.text}</pre>
     {result.url?<><p className="scanner-link-host">Website: <strong>{new URL(result.url).hostname}</strong></p><a className="button" href={result.url} target="_blank" rel="noopener noreferrer">Open link<ExternalLink size={16}/></a></>:<p className="scanner-hint">This code contains text or data. It does not contain a web link to open.</p>}
     <div className="scanner-actions"><Button className="secondary" onClick={async()=>{try{await navigator.clipboard.writeText(result.text);setCopied(true);}catch{setError('Copy is unavailable. Select the code contents and copy them manually.');}}}>{copied?<Check size={16}/>:<Copy size={16}/>} {copied?'Copied':'Copy contents'}</Button><Button className="ghost" onClick={clear}><ScanLine size={17}/>Scan another</Button></div>
    </>:<div className="scanner-result-empty"><span><Barcode size={35} strokeWidth={1.5}/></span><h2>Your result appears here</h2><p>{state==='reading'?'Reading the code in your image…':active?'Point your camera at a QR code or barcode.':'Start your camera or choose an image to read a QR code or barcode.'}</p><small>QR codes · Code 128 · Code 39 · EAN · UPC</small></div>}
   </section>
  </div>
 </>;
}
