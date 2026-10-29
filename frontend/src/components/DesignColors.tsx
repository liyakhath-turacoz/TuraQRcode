import {useState,type CSSProperties} from 'react';
import {Check, ChevronDown, Palette} from 'lucide-react';
import {Field} from '../shared/ui';
import type {Design} from '../shared/types';
import {featuredPalettes} from './qrPalettes';

export function luminance(hex:string) {
  const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);
  return rgb.reduce((sum,value,index)=>sum+(value<=.04045?value/12.92:((value+.055)/1.055)**2.4)*[.2126,.7152,.0722][index],0);
}

export function contrast(foreground:string,background:string) {
  const first=luminance(foreground),second=luminance(background);
  return (Math.max(first,second)+.05)/(Math.min(first,second)+.05);
}

export function readableInk(color:string) {
  return luminance(color)>.179?'#0f172a':'#ffffff';
}

export type QRStylePreset={
  name:string;
  foreground:string;
  foregroundEnd?:string;
  foregroundAngle?:number;
  background:string;
  end?:string;
  angle?:number;
  markerColor:string|null;
  foregroundStops?:string[];
  backgroundStops?:string[];
  gradient?:'linear'|'radial';
  descriptor:string;
};

type PaletteStop={name:string;start:string;end?:string;angle?:number};
const lightBackgrounds:PaletteStop[]=[
  {name:'Paper white',start:'#ffffff'}, {name:'Warm ivory',start:'#fffdf7'}, {name:'Cool mist',start:'#f8fafc'},
  {name:'Blue horizon',start:'#eff6ff',end:'#dbeafe',angle:35}, {name:'Mint wash',start:'#ecfdf5',end:'#d1fae5',angle:120},
  {name:'Soft sunrise',start:'#fff7ed',end:'#ffedd5',angle:35}, {name:'Lavender mist',start:'#faf5ff',end:'#ede9fe',angle:145},
];
const darkBackgrounds:PaletteStop[]=[
  {name:'True black',start:'#000000'}, {name:'Midnight fade',start:'#050816',end:'#14213d',angle:35},
  {name:'Forest night',start:'#031b17',end:'#064e3b',angle:135},
];
const darkInks:PaletteStop[]=[
  {name:'Black',start:'#000000'}, {name:'Charcoal',start:'#111827'}, {name:'Midnight blue',start:'#0f172a'},
  {name:'Signature blue',start:'#163b75'}, {name:'Ocean ink',start:'#075985'}, {name:'Forest ink',start:'#14532d'},
  {name:'Plum ink',start:'#4c1d95'}, {name:'Cobalt ink',start:'#1e40af'},
  {name:'Blue gradient',start:'#111827',end:'#163b75',angle:35}, {name:'Graphite gradient',start:'#111827',end:'#334155',angle:135},
];
const lightInks:PaletteStop[]=[
  {name:'White',start:'#ffffff'}, {name:'Soft white',start:'#f8fafc'}, {name:'Silver',start:'#e2e8f0'},
  {name:'Ice blue',start:'#bfdbfe'}, {name:'Clear cyan',start:'#a5f3fc'}, {name:'Mint',start:'#a7f3d0'},
  {name:'Warm gold',start:'#fde68a'}, {name:'Ice gradient',start:'#ffffff',end:'#bfdbfe',angle:35},
  {name:'Mint gradient',start:'#f8fafc',end:'#99f6e4',angle:135}, {name:'Rose gradient',start:'#fff1f2',end:'#fbcfe8',angle:35},
];
const safeContrast=(foreground:PaletteStop,background:PaletteStop)=>{
  const inks=[foreground.start,...(foreground.end?[foreground.end]:[])];
  const papers=[background.start,...(background.end?[background.end]:[])];
  return inks.every(ink=>papers.every(paper=>contrast(ink,paper)>=4.5));
};
const makePreset=(background:PaletteStop,foreground:PaletteStop,index:number):QRStylePreset=>{
  const lightPaper=luminance(background.start)>.5;
  const markerCandidates=lightPaper
    ? ['#163b75','#1e40af','#14532d','#4c1d95','#111827','#075985','#701a75']
    : ['#ffffff','#f8fafc','#bfdbfe','#a7f3d0','#fde68a','#fbcfe8'];
  const markerColor=markerCandidates.filter(color=>[background.start,...(background.end?[background.end]:[])].every(paper=>contrast(color,paper)>=4.5))[index%markerCandidates.length]||foreground.start;
  return {
    name:`${background.name} · ${foreground.name}`,
    foreground:foreground.start,foregroundEnd:foreground.end,foregroundAngle:foreground.angle||0,
    background:background.start,end:background.end,angle:background.angle||0,
    markerColor,
    descriptor:`${foreground.end?'Gradient ink':'Solid ink'} · ${background.end?'gradient background':'solid background'} · contrasting markers`,
  };
};
const legacyPresets:QRStylePreset[]= [...lightBackgrounds.map((background,backgroundIndex)=>
  darkInks.filter(ink=>safeContrast(ink,background)).map((ink,index)=>makePreset(background,ink,backgroundIndex+index)),
),...darkBackgrounds.map((background,backgroundIndex)=>
  lightInks.filter(ink=>safeContrast(ink,background)).map((ink,index)=>makePreset(background,ink,backgroundIndex+index)),
)].flat();
export const qrStylePresets=[...featuredPalettes,...legacyPresets];

export const textColorPresets=[
  {name:'White',value:'#ffffff'},
  {name:'Soft white',value:'#f8fafc'},
  {name:'Classic ink',value:'#0f172a'},
  {name:'Signature blue',value:'#163b75'},
  {name:'Ocean',value:'#075985'},
  {name:'Indigo',value:'#3730a3'},
  {name:'Forest',value:'#14532d'},
  {name:'Teal',value:'#134e4a'},
  {name:'Plum',value:'#701a75'},
  {name:'Charcoal',value:'#1e293b'},
];

export function isSafeTextColor(color:string,design:Design) {
  return (design.background_stops||[design.background,design.background_end||design.background]).every(background=>contrast(color,background)>=4.5);
}

function samePreset(design:Design,preset:QRStylePreset) {
  return design.foreground.toLowerCase()===preset.foreground
    && (design.foreground_end||'')===(preset.foregroundEnd||'')
    && Number(design.foreground_angle||0)===(preset.foregroundEnd?Number(preset.foregroundAngle||0):0)
    && design.background.toLowerCase()===preset.background
    && (design.background_end||'')===(preset.end||'')
    && Number(design.background_angle||0)===(preset.end?Number(preset.angle||0):0)
    && (preset.markerColor===null?!design.eye_color:(design.eye_color||design.foreground).toLowerCase()===preset.markerColor)
    && JSON.stringify(design.foreground_stops||[])===JSON.stringify(preset.foregroundStops||[])
    && JSON.stringify(design.background_stops||[])===JSON.stringify(preset.backgroundStops||[])
    && (design.foreground_gradient||'linear')===(preset.gradient||'linear');
}

export default function DesignColors({design,onChange,label,heading}:{design:Design;onChange:(value:Design)=>void;label?:string;showEyes?:boolean;heading?:string}) {
  if(heading)return <BarcodeColors design={design} onChange={onChange} label={label||'Bar color'} heading={heading}/>;
  const [open,setOpen]=useState(false);
  const [search,setSearch]=useState('');
  const active=qrStylePresets.find(preset=>samePreset(design,preset));
  const chosen=active||null;
  const select=(preset:QRStylePreset)=>{
    onChange({...design,foreground:preset.foreground,foreground_end:preset.foregroundEnd||null,foreground_angle:preset.foregroundEnd?(preset.foregroundAngle||0):0,background:preset.background,background_end:preset.end||null,background_angle:preset.end?(preset.angle||0):0,eye_color:preset.markerColor,top_text_color:preset.foreground,bottom_text_color:preset.foreground,foreground_stops:preset.foregroundStops||null,background_stops:preset.backgroundStops||null,foreground_gradient:preset.gradient||'linear',background_gradient:preset.gradient||'linear'});
    setOpen(false);
    setSearch('');
  };
  const gradient=(colors:string[],style:string,angle:number)=>style==='radial'?`radial-gradient(circle, ${colors.join(', ')})`:`linear-gradient(${angle}deg, ${colors.join(', ')})`;
  const fill=(preset:QRStylePreset)=>preset.end?gradient(preset.backgroundStops||[preset.background,preset.end],preset.gradient||'linear',preset.angle||0):preset.background;
  const inkFill=(preset:QRStylePreset)=>preset.foregroundEnd?gradient(preset.foregroundStops||[preset.foreground,preset.foregroundEnd],preset.gradient||'linear',preset.foregroundAngle||0):preset.foreground;
  const visiblePresets=qrStylePresets.filter(preset=>`${preset.name} ${preset.descriptor}`.toLowerCase().includes(search.trim().toLowerCase()));

  return <div className="qr-style-picker">
    <div className="qr-design-label">
      <span className="qr-design-icon"><Palette size={16}/></span>
      <div><h3>Color combinations</h3><p>Choose a coordinated QR, marker, and background palette. Your selected shapes stay the same.</p></div>
    </div>
    <button type="button" className="qr-style-trigger" aria-expanded={open} aria-controls="qr-style-options" onClick={()=>setOpen(value=>!value)}>
      <span className="qr-style-trigger-swatch" style={{background:chosen?fill(chosen):`linear-gradient(135deg, ${design.background}, ${design.background_end||design.background})`}}>
        <i style={{background:design.foreground_end?`linear-gradient(${design.foreground_angle||0}deg, ${design.foreground}, ${design.foreground_end})`:design.foreground}}/>
      </span>
      <span className="qr-style-trigger-copy"><strong>{chosen?.name||'Custom combination'}</strong><small>{chosen?.descriptor||'Your shape and color choices'}</small></span>
      <ChevronDown size={18} className={open?'is-open':''}/>
    </button>
    {open&&<div id="qr-style-options" className="qr-style-menu" role="group" aria-label="QR color combinations">
      <div className="qr-style-menu-heading"><strong>Choose a color combination</strong><span>{visiblePresets.length} of {qrStylePresets.length} palettes</span></div>
      <label className="sr-only" htmlFor="qr-style-search">Search QR palettes</label><input id="qr-style-search" className="qr-style-search" value={search} onChange={event=>setSearch(event.target.value)} placeholder="Search colors and backgrounds…"/>
      <div className="qr-style-grid">{visiblePresets.map(preset=>{
        const selected=chosen?.name===preset.name;
        return <button type="button" key={preset.name} className={`qr-style-option${selected?' selected':''}`} aria-pressed={selected} aria-label={`${preset.name}: ${preset.descriptor}`} onClick={()=>select(preset)}>
          <span className="qr-style-option-preview" style={{background:fill(preset)}}>
            <span className="qr-style-modules square" style={{'--qr-ink':preset.foreground,'--qr-fill':inkFill(preset)} as CSSProperties}>{Array.from({length:9},(_,index)=><i key={index}/>)}</span>
            <span className="qr-style-corners" style={{'--qr-ink':preset.markerColor||preset.foreground} as CSSProperties}><i/><b/></span>
          </span>
          <span className="qr-style-option-name">{preset.name}{selected&&<Check size={14}/>}</span>
          <span className="qr-style-option-description">{preset.descriptor}</span>
        </button>;
      })}</div>
    </div>}
  </div>;
}

function BarcodeColors({design,onChange,label,heading}:{design:Design;onChange:(value:Design)=>void;label:string;heading:string}){
  const colors=[{name:'Classic black',value:'#111827'},{name:'Signature blue',value:'#163b75'},{name:'Ocean',value:'#075985'},{name:'Forest',value:'#14532d'},{name:'Plum',value:'#701a75'}];
  return <div className="qr-colors barcode-colors">
    <div className="qr-design-label"><span className="qr-design-icon"><Palette size={16}/></span><div><h3>{heading}</h3><p>Choose a high-contrast ink color for a reliable scan.</p></div></div>
    <div className="qr-text-color-options" aria-label="Barcode ink colors">{colors.map(color=><button type="button" key={color.name} className={'qr-text-color-option '+(design.foreground.toLowerCase()===color.value?'selected':'')} aria-pressed={design.foreground.toLowerCase()===color.value} onClick={()=>onChange({...design,foreground:color.value,background:'#ffffff',background_end:null,background_angle:0})}><i style={{background:color.value}}/><span>{color.name}</span></button>)}</div>
    <Field label={label}><div className="color-field"><input aria-label={label} type="color" value={design.foreground} onChange={event=>onChange({...design,foreground:event.target.value,background:'#ffffff',background_end:null,background_angle:0})}/><span>{design.foreground.toUpperCase()}</span></div></Field>
  </div>;
}
