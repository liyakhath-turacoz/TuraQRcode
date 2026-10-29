import {useEffect,useRef,useState,type Dispatch,type SetStateAction} from 'react';
import {ImagePlus,Trash2,RotateCcw} from 'lucide-react';
import {message} from '../shared/api';
export type CardMedia={profile_image:string|null;cover_image:string|null;company_logo:string|null};
type Key=keyof CardMedia;
type Crop={zoom:number;x:number;y:number;mode:'fit'|'crop'};
const center=(key:Key):Crop=>({zoom:1,x:50,y:50,mode:key==='company_logo'?'fit':'crop'});
const fields=[
 {key:'profile_image',label:'Profile photo',width:512,height:512,minWidth:128,minHeight:128,hint:'Square portrait · 1:1'},
 {key:'cover_image',label:'Cover image',width:1280,height:720,minWidth:320,minHeight:180,hint:'Landscape cover · 16:9'},
 {key:'company_logo',label:'Company logo',width:512,height:512,minWidth:64,minHeight:64,hint:'Square canvas · Fit the full logo or crop to square'},
] as const;

function prepare(image:HTMLImageElement,key:Key,crop:Crop){
 const field=fields.find(item=>item.key===key)!;
 const canvas=document.createElement('canvas');canvas.width=field.width;canvas.height=field.height;
 const context=canvas.getContext('2d')!;
 context.imageSmoothingEnabled=true;context.imageSmoothingQuality='high';
 const scale=(crop.mode==='fit'?Math.min:Math.max)(field.width/image.width,field.height/image.height)*crop.zoom;
 const width=image.width*scale,height=image.height*scale;
 context.drawImage(image,(field.width-width)*crop.x/100,(field.height-height)*crop.y/100,width,height);
 let result=canvas.toDataURL('image/webp',.88);
 if(result.length>650_000)result=canvas.toDataURL('image/webp',.7);
 if(result.length>650_000)throw new Error('This image is too detailed. Choose a smaller image.');
 return result;
}

export default function CardMediaFields({value,onChange,onBusy,onError}:{value:CardMedia;onChange:Dispatch<SetStateAction<CardMedia>>;onBusy:(busy:boolean)=>void;onError:(error:string)=>void}){
 const [uploading,setUploading]=useState<Key|null>(null);
 const [crops,setCrops]=useState<Partial<Record<Key,Crop>>>({});
 const sources=useRef<Partial<Record<Key,{image:HTMLImageElement;url:string}>>>({});
 useEffect(()=>()=>{Object.values(sources.current).forEach(source=>URL.revokeObjectURL(source.url));},[]);
 function changeCrop(key:Key,crop:Crop){const source=sources.current[key];if(!source)return;try{const result=prepare(source.image,key,crop);setCrops(current=>({...current,[key]:crop}));onChange(current=>({...current,[key]:result}));onError('');}catch(error){onError(message(error));}}
 return <div className="card-media-fields">{fields.map(field=><div className="card-media-slot" key={field.key}>
  <div className={'card-media-thumbnail '+field.key}>{value[field.key]?<img src={value[field.key]!} alt={field.label}/>:<ImagePlus size={28}/>}</div>
  <label className="card-media-label">{field.label}<input type="file" aria-label={'Upload '+field.label.toLowerCase()} accept="image/png,image/jpeg,image/webp" disabled={uploading!==null} onChange={async event=>{
   const file=event.target.files?.[0];event.target.value='';if(!file)return;setUploading(field.key);onBusy(true);onError('');let address='';
   try{
    if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw new Error('Choose a PNG, JPG, or WebP image.');
    if(file.size>8_000_000)throw new Error('Choose an image smaller than 8 MB.');
    address=URL.createObjectURL(file);const image=new Image();image.src=address;await image.decode();
    if(image.width*image.height>30_000_000||image.width>8000||image.height>8000)throw new Error('Choose an image no larger than 8,000 px per side and 30 megapixels.');
    if(image.width<field.minWidth||image.height<field.minHeight)throw new Error(`${field.label}: use an image at least ${field.minWidth} × ${field.minHeight} pixels.`);
    const initialCrop=center(field.key);const result=prepare(image,field.key,initialCrop);
    if(sources.current[field.key])URL.revokeObjectURL(sources.current[field.key]!.url);
    sources.current[field.key]={image,url:address};address='';setCrops(current=>({...current,[field.key]:initialCrop}));onChange(current=>({...current,[field.key]:result}));
   }catch(error){onError(message(error));}finally{if(address)URL.revokeObjectURL(address);setUploading(null);onBusy(false);}
  }}/></label>
  <div className="card-media-size"><strong>{field.hint}</strong><span>Saved width: {field.width.toLocaleString()} px · Height: {field.height.toLocaleString()} px</span><span>Minimum upload: {field.minWidth} px wide × {field.minHeight} px high</span><span>Maximum: 8,000 px wide and 8,000 px high, within 30 megapixels. PNG, JPG, or WebP, up to 8 MB.</span>{sources.current[field.key]&&<span className="card-media-source">Original: {sources.current[field.key]!.image.width.toLocaleString()} × {sources.current[field.key]!.image.height.toLocaleString()} px</span>}</div>
  {uploading===field.key&&<small role="status">Preparing image…</small>}
  {value[field.key]&&!crops[field.key]&&<button type="button" className="text-link" disabled={uploading!==null} aria-label={'Adjust '+field.label.toLowerCase()+' crop'} onClick={async()=>{setUploading(field.key);onBusy(true);onError('');try{const image=new Image();image.src=value[field.key]!;await image.decode();sources.current[field.key]={image,url:image.src};setCrops(current=>({...current,[field.key]:center(field.key)}));}catch(error){onError(message(error));}finally{setUploading(null);onBusy(false);}}}>Adjust crop</button>}
  {crops[field.key]&&<div className="card-crop-controls" role="group" aria-label={field.label+' crop'}>
   {field.key==='company_logo'&&<label>Logo layout<select aria-label="Company logo layout" value={crops[field.key]!.mode} onChange={event=>changeCrop(field.key,{...center(field.key),mode:event.target.value as Crop['mode']})}><option value="fit">Fit entire logo</option><option value="crop">Crop to square</option></select></label>}
   {([{key:'zoom',label:'Zoom',min:1,max:3,step:.05},{key:'x',label:'Horizontal position',min:0,max:100,step:1},{key:'y',label:'Vertical position',min:0,max:100,step:1}] as const).map(control=><label key={control.key}>{control.label}<input type="range" aria-label={field.label+' '+control.label.toLowerCase()} min={control.min} max={control.max} step={control.step} value={crops[field.key]![control.key]} onChange={event=>changeCrop(field.key,{...crops[field.key]!,[control.key]:Number(event.target.value)})}/></label>)}
   <button type="button" className="text-link" aria-label={'Reset '+field.label.toLowerCase()+' crop'} onClick={()=>changeCrop(field.key,center(field.key))}><RotateCcw size={12}/>Reset crop</button>
  </div>}
  {value[field.key]&&<button type="button" className="text-link" disabled={uploading!==null} aria-label={'Remove '+field.label.toLowerCase()} onClick={()=>{const source=sources.current[field.key];if(source)URL.revokeObjectURL(source.url);delete sources.current[field.key];setCrops(current=>({...current,[field.key]:undefined}));onChange(current=>({...current,[field.key]:null}));}}><Trash2 size={13}/>Remove</button>}
 </div>)}</div>;
}
