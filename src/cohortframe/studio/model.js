/* Shared, dependency-free composer contract. The Python CLI remains authoritative. */
(function(root){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x));
const frames=(duration,fps)=>Math.max(1,Math.floor(duration*fps+0.5));
const scene=(id,title,subtitle,color)=>({id,title,subtitle,color,duration:4});
const templates={
 announcement:{version:1,name:'A new perspective',width:1280,height:720,fps:24,scenes:[scene('opening','A NEW PERSPECTIVE','A short introduction to your next idea.','#bc4d2c'),scene('idea','MAKE IT CLEAR','One message. A few deliberate frames.','#52775c'),scene('next','TAKE THE NEXT STEP','Give your audience somewhere to go.','#465c87')]},
 research:{version:1,name:'Research in focus',width:1280,height:720,fps:24,scenes:[scene('question','START WITH A QUESTION','What does your research ask?','#465c87'),scene('evidence','SHOW THE EVIDENCE','Summarise your finding and its source.','#52775c'),scene('limits','KEEP THE LIMITS VISIBLE','State what the evidence does not establish.','#bc4d2c')]},
 update:{version:1,name:'Project update',width:1280,height:720,fps:24,scenes:[scene('done','WHAT CHANGED','Describe the work completed.','#52775c'),scene('checked','WHAT WE CHECKED','Report the verification and its limits.','#465c87'),scene('next','WHAT COMES NEXT','Name the next useful step.','#bc4d2c')]}
};
function validate(m){
 const fail=message=>{throw Error(message)};
 const fields=(o,required,allowed,label)=>{if(!o||typeof o!=='object'||Array.isArray(o))fail(label+' must be an object.');for(const k of required)if(!Object.hasOwn(o,k))fail(label+' is missing '+k+'.');for(const k of Object.keys(o))if(!allowed.includes(k))fail(label+' has unsupported property '+k+'.');};
 const text=(v,label,max,empty=false,newline=false)=>{if(typeof v!=='string'||v.length>max||(!empty&&!v.trim()))fail(label+' must contain '+(empty?'0':'1')+' to '+max+' characters.');if(!(newline?/^[\x20-\x7e\n]*$/:/^[\x20-\x7e]*$/).test(v))fail(label+' supports printable ASCII'+(newline?' and line breaks':'')+'.');};
 fields(m,['version','name','width','height','fps','scenes'],['version','name','width','height','fps','scenes','audio'],'Project');
 if(m.version!==1)fail('Only project version 1 is supported.');text(m.name,'Project name',120);
 for(const dim of ['width','height'])if(!Number.isInteger(m[dim])||m[dim]<16||m[dim]>1920||m[dim]%2)fail(dim+' must be an even integer from 16 to 1920.');
 if(!Number.isInteger(m.fps)||m.fps<1||m.fps>30)fail('FPS must be an integer from 1 to 30.');
 if(!Array.isArray(m.scenes)||m.scenes.length<1||m.scenes.length>12)fail('Use 1 to 12 scenes.');
 const ids=new Set();let total=0,count=0;
 m.scenes.forEach((s,i)=>{const label='Scene '+(i+1);fields(s,['id','title','duration'],['id','title','duration','subtitle','color'],label);if(typeof s.id!=='string'||!(/^[A-Za-z][A-Za-z0-9_-]{0,63}$/).test(s.id)||ids.has(s.id))fail(label+' needs a unique valid ID.');ids.add(s.id);text(s.title,label+' title',160,false,true);if(s.subtitle!==undefined)text(s.subtitle,label+' subtitle',280,true,true);if(typeof s.duration!=='number'||!Number.isFinite(s.duration)||s.duration<=0||s.duration>60||s.duration*m.fps<1-1e-9)fail(label+' must last at least one frame and at most 60 seconds.');if(s.color!==undefined&&(typeof s.color!=='string'||!/^#[\da-f]{6}$/i.test(s.color)))fail(label+' needs a #RRGGBB colour.');total+=s.duration;count+=frames(s.duration,m.fps);});
 if(total>60+1e-9||count>60*m.fps)fail('Total duration, including frame rounding, must not exceed 60 seconds.');
 if(m.audio!==undefined){if(typeof m.audio!=='string'||!m.audio||m.audio.length>4096||/[\x00-\x1f]/.test(m.audio)||m.audio.includes('://')||/^(\/\/|\\\\)/.test(m.audio)||!m.audio.toLowerCase().endsWith('.wav'))fail('Soundtrack must be a local .wav path.');if(m.audio.split(/[\\/]/).includes('..'))fail('Soundtrack path must not contain parent traversal (..).');}
 if(new TextEncoder().encode(JSON.stringify(m)).length>131072)fail('Project exceeds 128 KiB.');
 return {frames:count,seconds:count/m.fps};
}
// Reject duplicate properties, excessive nesting and non-finite numbers before import.
function parse(source){
 if(new TextEncoder().encode(source).length>131072)throw Error('Project exceeds 128 KiB.');
 let i=0;const ws=()=>{while(/[\x20\t\r\n]/.test(source[i]||'x'))i++;};
 const string=()=>{const start=i++;while(i<source.length){if(source[i]==='\\'){i+=2;continue;}if(source[i++]==='"')return JSON.parse(source.slice(start,i));}throw Error('Unterminated JSON string.');};
 function value(depth=0){if(depth>64)throw Error('JSON nesting is too deep.');ws();const c=source[i];if(c==='"')return string();if(c==='{'||c==='['){i++;const object=c==='{',end=object?'}':']',out=object?Object.create(null):[],keys=new Set();ws();if(source[i]===end){i++;return out;}while(true){let k;if(object){ws();if(source[i]!=='"')throw Error('Expected JSON property name.');k=string();if(keys.has(k))throw Error('Duplicate JSON property: '+k);keys.add(k);ws();if(source[i++]!==':')throw Error('Expected colon.');}const v=value(depth+1);if(object)out[k]=v;else out.push(v);ws();if(source[i]===end){i++;return out;}if(source[i++]!==',')throw Error('Expected comma.');}}
 const match=source.slice(i).match(/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/);if(!match)throw Error('Invalid JSON value.');i+=match[0].length;const out=JSON.parse(match[0]);if(typeof out==='number'&&!Number.isFinite(out))throw Error('Non-finite number.');return out;}
 const result=value();ws();if(i!==source.length)throw Error('Unexpected text after JSON.');validate(result);return normalise(result);
}
function normalise(m){const n=clone(m);n.scenes.forEach(s=>{s.subtitle??='';s.color=(s.color||'#183153').toUpperCase()});return n;}
function newId(scenes){let n=1;while(scenes.some(s=>s.id==='scene'+n))n++;return 'scene'+n;}
function move(m,index,delta){const next=index+delta;if(next<0||next>=m.scenes.length)return index;[m.scenes[index],m.scenes[next]]=[m.scenes[next],m.scenes[index]];return next;}
const api={clone,frames,templates,validate,parse,normalise,newId,move};root.CF=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window==='undefined'?globalThis:window);
