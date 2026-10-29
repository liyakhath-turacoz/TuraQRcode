import {useState} from 'react';
import {ImagePlus,Trash2} from 'lucide-react';
import {message} from '../shared/api';
export type CardMedia={profile_image:string|null;cover_image:string|null;company_logo:string|null};

async function imageData(file:File){
 if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw new Error('Choose a PNG, JPG, or WebP image.');
 if(file.size>8_000_000)throw new Error('Choose an image smaller than 8 MB.');
 const address=URL.createObjectURL(file);
 try{
  const image=new Image();image.src=address;await image.decode();
  if(image.width*image.height>30_000_000)throw new Error('Choose an image smaller than 30 megapixels.');
  const ratio=Math.min(1,1024/Math.max(image.width,image.height));
  const canvas=document.createElement('canvas');canvas.width=Math.round(image.width*ratio);canvas.height=Math.round(image.height*ratio);
  canvas.getContext('2d')!.drawImage(image,0,0,canvas.width,canvas.height);
  let result=canvas.toDataURL('image/webp',.85);
  if(result.length>650_000)result=canvas.toDataURL('image/webp',.65);
  if(result.length>650_000)throw new Error('This image is too detailed. Choose a smaller image.');
  return result;
 }finally{URL.revokeObjectURL(address);}
}

export default function CardMediaFields({value,onChange,onBusy,onError}:{value:CardMedia;onChange:(value:CardMedia)=>void;onBusy:(busy:boolean)=>void;onError:(error:string)=>void}){
 const [uploading,setUploading]=useState<string|null>(null);
 const fields=[{key:'profile_image',label:'Profile photo'},{key:'cover_image',label:'Cover image'},{key:'company_logo',label:'Company logo'}] as const;
 return <div className="card-media-fields">{fields.map(field=><div className="card-media-slot" key={field.key}>
  <div className={'card-media-thumbnail '+field.key}>{value[field.key]?<img src={value[field.key]!} alt={field.label}/>:<ImagePlus size={28}/>}</div>
  <label className="card-media-label">{field.label}<input type="file" aria-label={'Upload '+field.label.toLowerCase()} accept="image/png,image/jpeg,image/webp" disabled={uploading!==null} onChange={async event=>{const file=event.target.files?.[0];event.target.value='';if(!file)return;setUploading(field.key);onBusy(true);onError('');try{onChange({...value,[field.key]:await imageData(file)});}catch(error){onError(message(error));}finally{setUploading(null);onBusy(false);}}}/></label>
  {uploading===field.key&&<small role="status">Preparing image…</small>}
  {value[field.key]&&<button type="button" className="text-link" aria-label={'Remove '+field.label.toLowerCase()} onClick={()=>onChange({...value,[field.key]:null})}><Trash2 size={13}/>Remove</button>}
 </div>)}</div>;
}
