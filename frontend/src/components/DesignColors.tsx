import {useState} from 'react';
import {Field} from '../shared/ui';
import type {Design} from '../shared/types';

export function luminance(hex:string){const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);return rgb.reduce((s,v,i)=>s+(v<=.04045?v/12.92:((v+.055)/1.055)**2.4)*[.2126,.7152,.0722][i],0);}
export function contrast(fg:string,bg:string){return (luminance(bg)+.05)/(luminance(fg)+.05);}
export function readableInk(color:string){return luminance(color)>.179?'#0f172a':'#ffffff';}
function darken(color:string){let rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16));while(contrast('#'+rgb.map(v=>v.toString(16).padStart(2,'0')).join(''),'#ffffff')<4.8)rgb=rgb.map(v=>Math.floor(v*.9));return '#'+rgb.map(v=>v.toString(16).padStart(2,'0')).join('');}
export default function DesignColors({design,onChange,label='QR color',showEyes=true}:{design:Design;onChange:(d:Design)=>void;label?:string;showEyes?:boolean}){
 const [notice,setNotice]=useState('');
 function change(field:'foreground'|'background'|'eye_color',color:string){let next={...design,[field]:color};let adjusted=false;
  if(field==='background'&&luminance(color)<.18){next.background='#ffffff';adjusted=true;}
  if(field==='foreground'||field==='eye_color'){const safe=darken(color);adjusted=safe!==color;next[field]=safe;}
  if(contrast(next.foreground,next.background)<4.5||contrast(next.eye_color||next.foreground,next.background)<4.5){next.background='#ffffff';adjusted=true;}
  setNotice(adjusted?'Colors adjusted to keep your code easy to scan.':'');onChange(next);
 }
 const colors=['#0f172a','#163b75','#1d4ed8','#4338ca','#701a75','#7f1d1d','#064e3b','#78350f'];
 const backgrounds=['#ffffff','#f8fafc','#eff6ff','#eef2ff','#fdf2f8','#fff7ed','#ecfdf5'];
 return <><div className="field-grid">{([{field:'foreground',label},{field:'background',label:'Background'}] as const).map(c=><Field key={c.field} label={c.label}><div className="color-field"><input type="color" aria-label={c.field==='background'?'Background color':label} value={design[c.field]} onChange={e=>change(c.field,e.target.value)}/><span>{design[c.field].toUpperCase()}</span></div><div className="color-swatches" aria-label={c.label+' suggestions'}>{(c.field==='foreground'?colors:backgrounds.filter(bg=>contrast(design.foreground,bg)>=4.5&&contrast(design.eye_color||design.foreground,bg)>=4.5)).map(color=><button type="button" key={color} aria-label={c.label+' '+color} aria-pressed={design[c.field]===color} style={{background:color}} onClick={()=>change(c.field,color)}/>)}</div></Field>)}</div><div className="contrast-status"><span>✓ Strong scan contrast</span><span>{contrast(design.foreground,design.background).toFixed(1)} : 1</span></div>{notice&&<p className="sublabel" role="status">{notice}</p>}{showEyes&&<Field label="Eye color" hint="The three corner markers help cameras recognize your code."><div className="color-field"><input aria-label="Eye color" type="color" value={design.eye_color||design.foreground} onChange={e=>change('eye_color',e.target.value)}/><span>{(design.eye_color||design.foreground).toUpperCase()}</span><button className="text-link" type="button" onClick={()=>onChange({...design,eye_color:null})}>Match QR color</button></div></Field>}</>;
}
