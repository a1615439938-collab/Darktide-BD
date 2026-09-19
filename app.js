(()=>{
"use strict";

/*
  Interaction model is informed by LawsonMode/darktide-tree-planner,
  whose README explicitly permits reuse/modification of its original editor code.
  Tree data and game icon art are sourced from Games Lantern / Darktide game assets.
*/

const DATA=window.TREE_DATA;
const ICONS=(DATA&&DATA.icons)||{};
const NS="http://www.w3.org/2000/svg";
const STORE="darktide-bilingual-editor-gl4";
const TREE_TOP=174;

const CAT={
  passive:{color:"#79b9c6",cn:"普通天赋",en:"Passive"},
  stat:{color:"#59616a",cn:"属性节点",en:"Stat"},
  blitz:{color:"#9edb70",cn:"闪击",en:"Blitz"},
  aura:{color:"#8bd178",cn:"光环",en:"Aura"},
  ability:{color:"#8ed9e7",cn:"主动技能",en:"Ability"},
  abilmod:{color:"#79a8c7",cn:"技能强化",en:"Ability modifier"},
  keystone:{color:"#d7b65a",cn:"关键节点",en:"Keystone"},
  keymod:{color:"#b89a52",cn:"关键强化",en:"Keystone modifier"},
  root:{color:"#d5d8dc",cn:"职业节点",en:"Class node"}
};

const EXCLUSIVE=new Set(["blitz","aura","ability","keystone"]);

let state={
  classKey:"veteran",
  selected:{},
  name:"",
  notes:"",
  zoom:1
};

let CUR=null;
let ROOT=null;
let active=new Set();
let adj={};
let nodeMap={};
let nodeEls={};
let edgeEls=[];
let exclusiveGroups={};
let hotSlug=null;

const $=q=>document.querySelector(q);

function load(){
  try{
    const raw=localStorage.getItem(STORE);
    if(raw) state={...state,...JSON.parse(raw)};
  }catch(_){}
}
function persist(){
  const name=$("#buildName");
  const notes=$("#notes");
  if(name) state.name=name.value||"";
  if(notes) state.notes=notes.value||"";
  try{localStorage.setItem(STORE,JSON.stringify(state));}catch(_){}
}
function classByKey(k){
  return DATA.classes.find(c=>c.key===k)||DATA.classes[0];
}
function radius(n){
  if(n.cat==="keystone")return 35;
  if(n.cat==="ability")return 34;
  if(n.cat==="blitz"||n.cat==="aura")return 31;
  if(n.cat==="root")return 32;
  if(n.cat==="stat")return 12;
  if(n.cat==="keymod"||n.cat==="abilmod")return 25;
  return 27;
}
function createSvg(tag,attrs={}){
  const el=document.createElementNS(NS,tag);
  for(const [k,v] of Object.entries(attrs)) el.setAttribute(k,v);
  return el;
}
function nodeShape(n,r){
  const color=(CAT[n.cat]||CAT.passive).color;
  let sh;
  if(n.shape==="s"){
    sh=createSvg("rect",{x:n.x-r,y:n.y-r,width:r*2,height:r*2,rx:5});
  }else if(n.shape==="d"){
    sh=createSvg("polygon",{points:`${n.x},${n.y-r} ${n.x+r},${n.y} ${n.x},${n.y+r} ${n.x-r},${n.y}`});
  }else if(n.shape==="h"){
    const pts=[];
    for(let i=0;i<6;i++){
      const a=Math.PI/3*i-Math.PI/6;
      pts.push(`${n.x+r*Math.cos(a)},${n.y+r*Math.sin(a)}`);
    }
    sh=createSvg("polygon",{points:pts.join(" ")});
  }else{
    sh=createSvg("circle",{cx:n.x,cy:n.y,r});
  }
  sh.setAttribute("class","shape");
  sh.setAttribute("stroke",color);
  return sh;
}
function clipShape(n,r,id){
  const cp=createSvg("clipPath",{id});
  let sh;
  const ir=Math.max(5,r-4);
  if(n.shape==="s"){
    sh=createSvg("rect",{x:n.x-ir,y:n.y-ir,width:ir*2,height:ir*2,rx:4});
  }else if(n.shape==="d"){
    sh=createSvg("polygon",{points:`${n.x},${n.y-ir} ${n.x+ir},${n.y} ${n.x},${n.y+ir} ${n.x-ir},${n.y}`});
  }else if(n.shape==="h"){
    const pts=[];
    for(let i=0;i<6;i++){
      const a=Math.PI/3*i-Math.PI/6;
      pts.push(`${n.x+ir*Math.cos(a)},${n.y+ir*Math.sin(a)}`);
    }
    sh=createSvg("polygon",{points:pts.join(" ")});
  }else{
    sh=createSvg("circle",{cx:n.x,cy:n.y,r:ir});
  }
  cp.appendChild(sh);
  return cp;
}
function initials(n){
  const words=String(n.en||n.cn||"?").replace(/[^A-Za-z0-9 ]/g," ").trim().split(/\s+/).filter(Boolean);
  if(!words.length) return "?";
  return (words.length===1?words[0].slice(0,2):words.slice(0,2).map(x=>x[0]).join("")).toUpperCase();
}
function iconFor(n){
  return ICONS[n.s]||null;
}
function buildExclusiveGroups(){
  exclusiveGroups={};
  for(const cat of EXCLUSIVE){
    const arr=CUR.nodes.filter(n=>n.cat===cat).slice().sort((a,b)=>a.y-b.y);
    let gi=0,last=-99999;
    for(const n of arr){
      if(n.y-last>90) gi++;
      last=n.y;
      exclusiveGroups[n.s]=cat+"#"+gi;
    }
  }
}
function currentGroupConflict(n){
  if(!EXCLUSIVE.has(n.cat)) return null;
  const grp=exclusiveGroups[n.s];
  for(const s of active){
    const other=nodeMap[s];
    if(other&&other.s!==n.s&&exclusiveGroups[other.s]===grp) return other;
  }
  return null;
}
function isAvail(slug){
  if(active.has(slug)) return false;
  for(const nb of adj[slug]||[]){
    if(active.has(nb)) return true;
  }
  return false;
}
function points(){
  return Math.max(0,active.size-1);
}
function saveSelection(){
  if(CUR) state.selected[CUR.key]=[...active].filter(s=>s!==ROOT);
}
function restoreSelection(){
  const wanted=new Set(state.selected[CUR.key]||[]);
  active=new Set([ROOT]);
  let progressed=true;
  while(progressed){
    progressed=false;
    for(const s of [...wanted]){
      const n=nodeMap[s];
      if(!n||!isAvail(s)||points()>=CUR.budget) continue;
      if(currentGroupConflict(n)) continue;
      active.add(s);
      wanted.delete(s);
      progressed=true;
    }
  }
}
function renderClassbar(){
  const bar=$("#classbar");
  bar.innerHTML="";
  for(const c of DATA.classes){
    const b=document.createElement("button");
    b.type="button";
    b.className=c.key===state.classKey?"on":"";
    b.innerHTML=`<span>${c.cn}</span> · <span>${c.name}</span>`;
    b.onclick=()=>{
      saveSelection();
      state.classKey=c.key;
      persist();
      renderAll(true);
    };
    bar.appendChild(b);
  }
}
function renderNode(svg,defs,n){
  const r=radius(n);
  const g=createSvg("g",{class:"node"+(n.cat==="stat"?" stat":""),"data-s":n.s});
  g.appendChild(nodeShape(n,r));
  if(n.cat!=="stat"){
    const inner=nodeShape(n,Math.max(7,r-4));
    inner.setAttribute("class","inner-frame");
    g.appendChild(inner);
  }

  const src=iconFor(n);
  if(src&&n.cat!=="stat"){
    const id="clip_"+n.s.replace(/[^a-z0-9]/gi,"_");
    defs.appendChild(clipShape(n,r,id));
    const im=createSvg("image",{
      href:src,
      x:n.x-r+5,
      y:n.y-r+5,
      width:(r-5)*2,
      height:(r-5)*2,
      preserveAspectRatio:"xMidYMid slice",
      "clip-path":"url(#"+id+")",
      class:"art"
    });
    g.appendChild(im);
  }else{
    const tx=createSvg("text",{x:n.x,y:n.y,class:"fallback"});
    tx.textContent=n.cat==="stat"?"•":initials(n);
    g.appendChild(tx);
  }

  const title=createSvg("title");
  title.textContent=(n.cn&&n.cn!==n.en?n.cn+" / ":"")+(n.en||"");
  g.appendChild(title);

  g.addEventListener("click",e=>{
    e.stopPropagation();
    hotSlug=n.s;
    showInfo(n);
    toggleNode(n);
    redraw();
  });

  svg.appendChild(g);
  nodeEls[n.s]=g;
}
function buildTree(){
  CUR=classByKey(state.classKey);
  state.classKey=CUR.key;

  const svg=$("#treeSvg");
  svg.innerHTML="";
  const defs=createSvg("defs");
  svg.appendChild(defs);

  nodeMap={};
  adj={};
  nodeEls={};
  edgeEls=[];

  for(const n of CUR.nodes){
    nodeMap[n.s]=n;
    adj[n.s]=new Set();
  }

  ROOT=(CUR.nodes.find(n=>n.cat==="root")||CUR.nodes.slice().sort((a,b)=>a.y-b.y)[0]).s;

  for(const [a,b] of CUR.edges){
    if(!nodeMap[a]||!nodeMap[b]) continue;
    adj[a].add(b);
    adj[b].add(a);
    const na=nodeMap[a],nb=nodeMap[b];
    const line=createSvg("line",{x1:na.x,y1:na.y,x2:nb.x,y2:nb.y,class:"edge"});
    svg.appendChild(line);
    edgeEls.push({el:line,a,b});
  }

  buildExclusiveGroups();
  restoreSelection();

  for(const n of CUR.nodes) renderNode(svg,defs,n);

  const [x,y,w,h]=CUR.viewbox;
  svg.setAttribute("viewBox",`${x} ${y} ${w} ${h}`);
  applyZoom();
  redraw();

  const first=nodeMap[hotSlug]&&nodeMap[hotSlug]||nodeMap[ROOT];
  showInfo(first,true);
}
function toggleNode(n){
  if(n.s===ROOT) return;

  if(active.has(n.s)){
    const trial=new Set(active);
    trial.delete(n.s);

    const seen=new Set([ROOT]);
    const q=[ROOT];
    while(q.length){
      const cur=q.pop();
      for(const nb of adj[cur]||[]){
        if(trial.has(nb)&&!seen.has(nb)){
          seen.add(nb);
          q.push(nb);
        }
      }
    }

    if([...trial].some(s=>s!==ROOT&&!seen.has(s))){
      setStatus("不能移除：后续天赋仍通过此节点连接。 / Cannot remove: downstream talents route through this node.","err");
      return;
    }
    active.delete(n.s);
  }else{
    if(!isAvail(n.s)){
      setStatus("该节点尚未连接到已选择路径。 / This node is not connected to your selected path.","err");
      return;
    }
    if(points()>=CUR.budget){
      setStatus("30 点已用完。 / All 30 talent points are spent.","err");
      return;
    }
    const conflict=currentGroupConflict(n);
    if(conflict){
      setStatus(`同一选择组只能点一个：${conflict.cn||conflict.en} / Only one choice is allowed in this group.`,"err");
      return;
    }
    active.add(n.s);
  }

  saveSelection();
  persist();
}
function redraw(){
  for(const n of CUR.nodes){
    const g=nodeEls[n.s];
    if(!g) continue;
    g.classList.remove("active","avail","locked","hot");
    if(active.has(n.s)) g.classList.add("active");
    else if(isAvail(n.s)) g.classList.add("avail");
    else g.classList.add("locked");
    if(n.s===hotSlug) g.classList.add("hot");
  }

  for(const e of edgeEls){
    e.el.classList.toggle("on",active.has(e.a)&&active.has(e.b));
  }

  $("#pts").textContent=`${points()} / ${CUR.budget}`;
  setStatus(`${CUR.cn} · ${CUR.name} — ${DATA.version} — ${CUR.nodes.length} nodes`,"ok");
}
function showInfo(n,boot=false){
  if(!n) return;
  const cat=CAT[n.cat]||CAT.passive;

  $("#infoType").textContent=`${cat.cn} / ${cat.en}`;
  $("#infoCn").textContent=(n.cn&&n.cn!==n.en)?n.cn:(n.en||"");
  $("#infoEn").textContent=n.en||"";

  let stateText="已选择 / Selected";
  if(n.s===ROOT) stateText="职业起点 / Root";
  else if(!active.has(n.s)) stateText=isAvail(n.s)?"可选择 / Available":"未连接 / Locked";
  $("#infoState").textContent=stateText;

  if(n.desc){
    $("#infoCnDesc").textContent="效果数值以英文原文为准；中文天赋名用于对照学习。";
    $("#infoDesc").textContent=n.desc;
  }else{
    $("#infoCnDesc").textContent="该预览节点暂时没有可靠的效果说明。";
    $("#infoDesc").textContent="No reliable preview effect text is available for this node yet.";
  }

  if(!boot){
    const card=$("#talentCard");
    const top=card.getBoundingClientRect().top+window.scrollY-85;
    if(Math.abs(window.scrollY-top)>500) window.scrollTo({top,behavior:"smooth"});
  }
}
function setStatus(msg,type=""){
  const el=$("#status");
  el.textContent=msg;
  el.className="status"+(type?" "+type:"");
}
function applyZoom(){
  if(!CUR) return;
  const svg=$("#treeSvg");
  const wrap=document.querySelector(".tree-wrap");
  const vw=CUR.viewbox[2],vh=CUR.viewbox[3];
  const base=Math.max(320,Math.min(720,wrap.clientWidth-4));
  const width=base*state.zoom;
  svg.style.width=width+"px";
  svg.style.height=(width*vh/vw)+"px";
}
function renderAll(resetScroll=false){
  renderClassbar();
  $("#buildName").value=state.name||"";
  $("#notes").value=state.notes||"";
  hotSlug=null;
  buildTree();
  if(resetScroll) window.scrollTo({top:0,behavior:"smooth"});
}
function exportData(){
  saveSelection();
  persist();
  return JSON.stringify({
    format:"Darktide-Future-Tree-BD-2",
    patch:DATA.version,
    classKey:state.classKey,
    selected:state.selected,
    name:state.name,
    notes:state.notes
  },null,2);
}
function importData(txt){
  const x=JSON.parse(txt);
  if(!["Darktide-Future-Tree-BD-1","Darktide-Future-Tree-BD-2"].includes(x.format)){
    throw new Error("不是本规划器的 BD 数据 / Unsupported build format");
  }
  state.classKey=x.classKey||state.classKey;
  state.selected=x.selected||{};
  state.name=x.name||"";
  state.notes=x.notes||"";
  persist();
  renderAll(false);
}
function bind(){
  $("#resetBtn").onclick=()=>{
    if(confirm("重置当前职业的天赋？ / Reset this class tree?")){
      state.selected[state.classKey]=[];
      hotSlug=null;
      persist();
      renderAll(false);
    }
  };
  $("#saveBtn").onclick=()=>{
    saveSelection();
    persist();
    const b=$("#saveBtn"),old=b.innerHTML;
    b.innerHTML="已保存 ✓<br><small>Saved</small>";
    setTimeout(()=>b.innerHTML=old,900);
  };
  $("#zoomIn").onclick=()=>{
    state.zoom=Math.min(1.9,state.zoom*1.15);
    applyZoom();
    persist();
  };
  $("#zoomOut").onclick=()=>{
    state.zoom=Math.max(.72,state.zoom/1.15);
    applyZoom();
    persist();
  };
  $("#zoomFit").onclick=()=>{
    state.zoom=1;
    applyZoom();
    persist();
    document.querySelector(".tree-wrap").scrollLeft=0;
  };
  $("#buildName").oninput=()=>{state.name=$("#buildName").value;persist();};
  $("#notes").oninput=()=>{state.notes=$("#notes").value;persist();};

  $("#exportBtn").onclick=()=>{
    $("#codeBox").value=exportData();
    $("#dialogMsg").textContent="";
    $("#codeDialog").showModal();
  };
  $("#importBtn").onclick=()=>{
    $("#codeBox").value="";
    $("#dialogMsg").textContent="粘贴 BD 数据后点击“载入” / Paste build data, then tap Load.";
    $("#codeDialog").showModal();
  };
  $("#copyBtn").onclick=async()=>{
    const text=$("#codeBox").value;
    try{
      await navigator.clipboard.writeText(text);
      $("#dialogMsg").textContent="已复制 / Copied ✓";
    }catch(_){
      $("#codeBox").select();
      document.execCommand("copy");
      $("#dialogMsg").textContent="已复制 / Copied ✓";
    }
  };
  $("#loadBtn").onclick=()=>{
    try{
      importData($("#codeBox").value);
      $("#dialogMsg").textContent="载入成功 / Loaded ✓";
      setTimeout(()=>$("#codeDialog").close(),450);
    }catch(e){
      $("#dialogMsg").textContent=e.message;
    }
  };

  addEventListener("resize",applyZoom);
}
function selfCheck(){
  if(!DATA||!Array.isArray(DATA.classes)||!DATA.classes.length) throw new Error("tree-data.js not loaded");
  if(!DATA.icons||Object.keys(DATA.icons).length<50) throw new Error("talent icons are missing");
  if(!CUR||CUR.nodes.length<40) throw new Error("talent tree data is incomplete");
  if(!ROOT||!nodeMap[ROOT]) throw new Error("class root is missing");
  if(Object.keys(nodeEls).length!==CUR.nodes.length) throw new Error("not all nodes rendered");
}

try{
  load();
  bind();
  renderAll(false);
  selfCheck();
  if("serviceWorker" in navigator){
    window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js?v=gl3").catch(()=>{}));
  }
}catch(e){
  setStatus("天赋树启动失败 / Talent tree failed to start: "+e.message,"err");
}
})();