import {useEffect,useState} from 'react';
import QRCode from 'qrcode';
export default function QRThumb({value}:{value:string}){const [src,setSrc]=useState('');useEffect(()=>{let active=true;QRCode.toDataURL(value,{width:100,margin:2,color:{dark:'#193c34',light:'#ffffff'}}).then(url=>{if(active)setSrc(url);}).catch(()=>{});return()=>{active=false;};},[value]);return src?<img src={src} alt="" className="mini-qr"/>:<span className="mini-qr"/>;}
