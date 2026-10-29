import {useEffect,useId} from 'react';
import {EditorContent,useEditor,useEditorState} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Superscript from '@tiptap/extension-superscript';
import Subscript from '@tiptap/extension-subscript';
import CharacterCount from '@tiptap/extension-character-count';
import Placeholder from '@tiptap/extension-placeholder';
import DOMPurify from 'dompurify';
import {Bold,Italic,Underline,Strikethrough,Code,Superscript as SupIcon,Subscript as SubIcon,List,ListOrdered,IndentIncrease,IndentDecrease,Undo2,Redo2,RemoveFormatting,Quote} from 'lucide-react';

const tags=['p','br','strong','b','em','i','u','s','strike','code','sup','sub','ul','ol','li','blockquote'];
export function safeProfileHTML(html:string){return DOMPurify.sanitize(html,{ALLOWED_TAGS:tags,ALLOWED_ATTR:[]});}
export function RichText({text,html}:{text:string;html?:string}){
 return html?<div className="profile-rich-text" dangerouslySetInnerHTML={{__html:safeProfileHTML(html)}}/>:<p className="profile-plain-text">{text}</p>;
}
function initialContent(text:string,html:string){
 if(html)return safeProfileHTML(html);
 return {type:'doc',content:(text||'').split('\n').map(line=>({type:'paragraph',...(line?{content:[{type:'text',text:line}]}:{})}))};
}

export default function RichTextEditor({label,text,html='',limit,required=false,placeholder='',onChange}:{label:string;text:string;html?:string;limit:number;required?:boolean;placeholder?:string;onChange:(text:string,html:string)=>void}){
 const id=useId();
 const editor=useEditor({
  extensions:[StarterKit.configure({heading:false,codeBlock:false,horizontalRule:false,link:false,trailingNode:false}),Superscript,Subscript,CharacterCount.configure({limit}),Placeholder.configure({placeholder})],
  content:initialContent(text,html),
  editorProps:{attributes:{id,role:'textbox','aria-label':label,'aria-multiline':'true','aria-required':String(required),'aria-describedby':id+'-count'}},
  onUpdate:({editor})=>onChange(editor.getText({blockSeparator:'\n'}),editor.isEmpty?'':editor.getHTML()),
 });
 const state=useEditorState({editor,selector:({editor:e})=>e?{
  count:e.storage.characterCount.characters(),bold:e.isActive('bold'),italic:e.isActive('italic'),underline:e.isActive('underline'),strike:e.isActive('strike'),code:e.isActive('code'),superscript:e.isActive('superscript'),subscript:e.isActive('subscript'),bulletList:e.isActive('bulletList'),orderedList:e.isActive('orderedList'),blockquote:e.isActive('blockquote'),
  undo:e.can().undo(),redo:e.can().redo(),indent:e.can().sinkListItem('listItem'),outdent:e.can().liftListItem('listItem'),
 }:null});
 useEffect(()=>{if(!editor)return;const current=editor.getHTML();if(html?current!==html:editor.getText({blockSeparator:'\n'})!==text)editor.commands.setContent(initialContent(text,html),{emitUpdate:false});},[editor,text,html]);
 if(!editor||!state)return null;
 const buttons=[
  {name:'Bold',icon:Bold,active:state.bold,run:()=>editor.chain().focus().toggleBold().run()},
  {name:'Italic',icon:Italic,active:state.italic,run:()=>editor.chain().focus().toggleItalic().run()},
  {name:'Underline',icon:Underline,active:state.underline,run:()=>editor.chain().focus().toggleUnderline().run()},
  {name:'Strikethrough',icon:Strikethrough,active:state.strike,run:()=>editor.chain().focus().toggleStrike().run()},
  {name:'Inline code',icon:Code,active:state.code,run:()=>editor.chain().focus().toggleCode().run()},
  {name:'Superscript',icon:SupIcon,active:state.superscript,run:()=>editor.chain().focus().unsetSubscript().toggleSuperscript().run()},
  {name:'Subscript',icon:SubIcon,active:state.subscript,run:()=>editor.chain().focus().unsetSuperscript().toggleSubscript().run()},
  {name:'Bullet list',icon:List,active:state.bulletList,run:()=>editor.chain().focus().toggleBulletList().run()},
  {name:'Numbered list',icon:ListOrdered,active:state.orderedList,run:()=>editor.chain().focus().toggleOrderedList().run()},
  {name:'Quote',icon:Quote,active:state.blockquote,run:()=>editor.chain().focus().toggleBlockquote().run()},
  {name:'Indent list',icon:IndentIncrease,disabled:!state.indent,run:()=>editor.chain().focus().sinkListItem('listItem').run()},
  {name:'Outdent list',icon:IndentDecrease,disabled:!state.outdent,run:()=>editor.chain().focus().liftListItem('listItem').run()},
  {name:'Undo',icon:Undo2,disabled:!state.undo,run:()=>editor.chain().focus().undo().run()},
  {name:'Redo',icon:Redo2,disabled:!state.redo,run:()=>editor.chain().focus().redo().run()},
  {name:'Clear formatting',icon:RemoveFormatting,run:()=>editor.chain().focus().unsetAllMarks().clearNodes().run()},
 ];
 return <div className="field rich-text-field"><label htmlFor={id}>{label}</label><div className="rich-editor"><div className="rich-toolbar" role="group" aria-label={label+' formatting'}>{buttons.map(item=><button key={item.name} type="button" title={item.name} aria-label={item.name} aria-pressed={item.active} disabled={item.disabled} onMouseDown={event=>event.preventDefault()} onClick={item.run}><item.icon size={16}/></button>)}</div><EditorContent editor={editor}/></div><small id={id+'-count'}>{state.count.toLocaleString()} / {limit.toLocaleString()} characters{required?' · Required':''}</small></div>;
}
