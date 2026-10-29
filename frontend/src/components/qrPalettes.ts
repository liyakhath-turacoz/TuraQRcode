import families from './qrGradientFamilies.json';
import type {QRStylePreset} from './DesignColors';

const classics:QRStylePreset[]=[
 {name:'Classic black & white',foreground:'#000000',background:'#ffffff',markerColor:'#000000',descriptor:'Classic · black QR and markers on white'},
 {name:'Classic white on black',foreground:'#ffffff',background:'#000000',markerColor:'#ffffff',descriptor:'Inverted · white QR and markers on black'},
];
const gradients:QRStylePreset[]=families.flatMap(family=>(['linear','radial'] as const).flatMap(gradient=>{
 const create=(name:string,foreground:string,background:string,foregroundStops?:string[],backgroundStops?:string[]):QRStylePreset=>({name:`${family.name} ${name} · ${gradient}`,foreground,background,foregroundStops,backgroundStops,foregroundEnd:foregroundStops?.at(-1),end:backgroundStops?.at(-1),foregroundAngle:135,angle:135,markerColor:null,gradient,descriptor:`${foregroundStops?'Multicolor QR':'Solid QR'} · ${backgroundStops?'multicolor background':'plain background'} · ${gradient}`});
 return [create('gradient on white',family.dark[0],'#ffffff',family.dark),create('pastel background','#000000',family.light[0],undefined,family.light),create('white on gradient','#ffffff',family.dark[0],undefined,family.dark),create('gradient on black',family.light[0],'#000000',family.light),create('coordinated gradients',family.dark[0],family.light[0],family.dark,family.light),create('inverted gradients',family.light[0],family.dark[0],family.light,family.dark)];
}));
export const featuredPalettes=[...classics,...gradients];
