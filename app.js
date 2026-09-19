(()=>{
"use strict";
const DATA=window.TREE_DATA;
const NS="http://www.w3.org/2000/svg";
const STORE="darktide-real-tree-v1";
const CAT={
  passive:{color:"#3fb0bd",cn:"普通天赋",en:"Passive"},
  stat:{color:"#7a8089",cn:"属性节点",en:"Stat"},
  blitz:{color:"#d98a3d",cn:"闪击",en:"Blitz"},
  aura:{color:"#5fb06a",cn:"光环",en:"Aura"},
  ability:{color:"#a583d6",cn:"主动技能",en:"Ability"},
  abilmod:{color:"#7d6bb0",cn:"技能强化",en:"Ability modifier"},
  keystone:{color:"#e0b23c",cn:"关键节点",en:"Keystone"},
  keymod:{color:"#b89a52",cn:"关键强化",en:"Keystone modifier"},
  root:{color:"#c9ccd1",cn:"职业节点",en:"Class node"}
};
const EXCLUSIVE=new Set(["blitz","aura","ability","keystone"]);
let state={classKey:"veteran",selected:{},name:"",notes:"",zoom:1.28};
let CUR=null,ROOT=null,active=new Set(),adj={},nodeMap={},nodeEls={},edgeEls=[],exclusiveGroups={};

const $=q=>document.querySelector(q);
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));

function load(){
  try{const raw=localStorage.getItem(STORE);if(raw)state={...state,...JSON.parse(raw)};}catch(e){}
}
function persist(){
  state.name=$("#buildName").value||"";
  state.notes=$("#notes").value||"";
  try{localStorage.setItem(STORE,JSON.stringify(state));}catch(e){}
}
function classByKey(k){return DATA.classes.find(c=>c.key===k)||DATA.classes[0];}
function radius(n){return n.cat==="keystone"?34:(["ability","blitz","aura","root"].includes(n.cat)?29:(n.cat==="stat"?13:23));}
function initials(n){
  const s=(n.en||n.cn||"?").replace(/[^A-Za-z0-9 ]/g," ").trim().split(/\s+/).filter(Boolean);
  if(!s.length)return "?";
  return (s.length===1?s[0].slice(0,2):s.slice(0,2).map(x=>x[0]).join("")).toUpperCase();
}
function createSvg(tag,attrs={}){
  const el=document.createElementNS(NS,tag);
  Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));
  return el;
}
function shapeFor(n,r){
  const color=(CAT[n.cat]||CAT.passive).color;
  let sh;
  if(n.shape==="s"){
    sh=createSvg("rect",{x:n.x-r,y:n.y-r,width:r*2,height:r*2,rx:7});
  }else if(n.shape==="d"){
    sh=createSvg("polygon",{points:`${n.x},${n.y-r} ${n.x+r},${n.y} ${n.x},${n.y+r} ${n.x-r},${n.y}`});
  }else if(n.shape==="h"){
    const pts=[];
    for(let i=0;i<6;i++){const a=Math.PI/3*i-Math.PI/6;pts.push(`${n.x+r*Math.cos(a)},${n.y+r*Math.sin(a)}`);}
    sh=createSvg("polygon",{points:pts.join(" ")});
  }else{
    sh=createSvg("circle",{cx:n.x,cy:n.y,r});
  }
  sh.setAttribute("class","shape");
  sh.setAttribute("stroke",color);
  return sh;
}
function splitLabel(s,max=13){
  const words=String(s||"").split(/\s+/).filter(Boolean);
  if(words.length<=1)return [String(s||"")];
  const out=[];let cur="";
  words.forEach(w=>{
    const next=(cur+" "+w).trim();
    if(next.length>max&&cur){out.push(cur);cur=w;}else cur=next;
  });
  if(cur)out.push(cur);
  return out.slice(0,2);
}
function addTextLines(g,n,r){
  if(n.cat==="stat"||n.cat==="root")return;
  const cn=(n.cn&&n.cn!==n.en)?n.cn:"";
  const en=n.en||"";
  let y=n.y+r+17;
  if(cn){
    const t=createSvg("text",{x:n.x,y,class:"label-cn"});
    splitLabel(cn,9).forEach((line,i)=>{const sp=createSvg("tspan",{x:n.x,dy:i?17:0});sp.textContent=line;t.appendChild(sp);});
    g.appendChild(t);
    y+=splitLabel(cn,9).length*17+2;
  }
  const t2=createSvg("text",{x:n.x,y,class:"label-en"});
  splitLabel(en,14).forEach((line,i)=>{const sp=createSvg("tspan",{x:n.x,dy:i?14:0});sp.textContent=line;t2.appendChild(sp);});
  g.appendChild(t2);
}
function buildExclusiveGroups(){
  exclusiveGroups={};
  for(const cat of EXCLUSIVE){
    const arr=CUR.nodes.filter(n=>n.cat===cat).slice().sort((a,b)=>a.y-b.y);
    let gi=0,last=-99999;
    arr.forEach(n=>{if(n.y-last>90)gi++;last=n.y;n._grp=cat+"#"+gi;exclusiveGroups[n.s]=n._grp;});
  }
}
function currentGroupConflict(n){
  if(!EXCLUSIVE.has(n.cat))return null;
  const grp=exclusiveGroups[n.s];
  for(const s of active){
    const other=nodeMap[s];
    if(other&&other.s!==n.s&&exclusiveGroups[other.s]===grp)return other;
  }
  return null;
}
function isAvail(s){
  if(active.has(s))return false;
  return [...(adj[s]||[])].some(x=>active.has(x));
}
function countPoints(){return Math.max(0,active.size-1);}
function renderClassbar(){
  const bar=$("#classbar");bar.innerHTML="";
  DATA.classes.forEach(c=>{
    const b=document.createElement("button");
    b.type="button";b.className=c.key===state.classKey?"on":"";
    b.textContent=`${c.cn} · ${c.name}`;
    b.onclick=()=>{saveSelection();state.classKey=c.key;persist();renderAll(true);};
    bar.appendChild(b);
  });
}
function saveSelection(){
  if(!CUR)return;
  state.selected[CUR.key]=[...active].filter(x=>x!==ROOT);
}
function restoreSelection(){
  const wanted=new Set(state.selected[CUR.key]||[]);
  active=new Set([ROOT]);
  // Restore only connected nodes, iterating until no progress.
  let changed=true;
  while(changed){
    changed=false;
    for(const s of [...wanted]){
      if(nodeMap[s]&&isAvail(s)&&countPoints()<CUR.budget){
        const conflict=currentGroupConflict(nodeMap[s]);
        if(!conflict){active.add(s);wanted.delete(s);changed=true;}
      }
    }
  }
}
function buildTree(){
  CUR=classByKey(state.classKey);
  state.classKey=CUR.key;
  const svg=$("#treeSvg");svg.innerHTML="";
  nodeMap={};adj={};nodeEls={};edgeEls=[];
  CUR.nodes.forEach(n=>{nodeMap[n.s]=n;adj[n.s]=new Set();});
  ROOT=(CUR.nodes.find(n=>n.cat==="root")||CUR.nodes.slice().sort((a,b)=>a.y-b.y)[0]).s;
  CUR.edges.forEach(([a,b])=>{
    if(!nodeMap[a]||!nodeMap[b])return;
    adj[a].add(b);adj[b].add(a);
    const na=nodeMap[a],nb=nodeMap[b];
    const line=createSvg("line",{x1:na.x,y1:na.y,x2:nb.x,y2:nb.y,class:"edge"});
    svg.appendChild(line);edgeEls.push({el:line,a,b});
  });
  buildExclusiveGroups();
  restoreSelection();
  CUR.nodes.forEach(n=>{
    const r=radius(n);
    const g=createSvg("g",{class:"node","data-s":n.s});
    g.appendChild(shapeFor(n,r));
    const tx=createSvg("text",{x:n.x,y:n.y,class:"mini"});
    tx.textContent=n.cat==="stat"?"+" : initials(n);
    g.appendChild(tx);
    addTextLines(g,n,r);
    g.addEventListener("click",e=>{e.stopPropagation();showInfo(n);toggleNode(n);});
    svg.appendChild(g);nodeEls[n.s]=g;
  });
  const [x,y,w,h]=CUR.viewbox;
  svg.setAttribute("viewBox",`${x} ${y} ${w} ${h}`);
  applyZoom();
  redraw();
  showInfo(nodeMap[ROOT],true);
}
function toggleNode(n){
  if(n.s===ROOT)return;
  if(active.has(n.s)){
    const trial=new Set(active);trial.delete(n.s);
    const seen=new Set([ROOT]),q=[ROOT];
    while(q.length){
      const cur=q.pop();
      for(const nb of adj[cur]||[]){if(trial.has(nb)&&!seen.has(nb)){seen.add(nb);q.push(nb);}}
    }
    if([...trial].some(s=>s!==ROOT&&!seen.has(s))){
      setStatus("不能移除：后续天赋仍依赖这个节点。 / Cannot remove: downstream talents depend on it.","err");
      return;
    }
    active.delete(n.s);
  }else{
    if(!isAvail(n.s)){
      setStatus("该节点尚未与已选择路径相连。 / This node is not connected to your selected path.","err");
      return;
    }
    if(countPoints()>=CUR.budget){
      setStatus("已经用完 30 点。 / All 30 points are spent.","err");return;
    }
    const conflict=currentGroupConflict(n);
    if(conflict){
      setStatus(`同一组只能选择一个：${conflict.cn||conflict.en} / Only one choice in this group.`,"err");return;
    }
    active.add(n.s);
  }
  saveSelection();persist();redraw();showInfo(n);
}
function redraw(){
  CUR.nodes.forEach(n=>{
    const g=nodeEls[n.s];if(!g)return;
    g.classList.remove("active","avail","locked");
    if(active.has(n.s))g.classList.add("active");
    else if(isAvail(n.s))g.classList.add("avail");
    else g.classList.add("locked");
  });
  edgeEls.forEach(e=>e.el.classList.toggle("on",active.has(e.a)&&active.has(e.b)));
  $("#pts").textContent=`${countPoints()} / ${CUR.budget}`;
  setStatus(`${CUR.cn} · ${CUR.name} — ${DATA.version} — ${CUR.nodes.length} 个节点 / nodes`,"ok");
}
function showInfo(n,boot=false){
  if(!n)return;
  const cat=CAT[n.cat]||CAT.passive;
  $("#infoType").textContent=`${cat.cn} / ${cat.en}`;
  $("#infoCn").textContent=(n.cn&&n.cn!==n.en)?n.cn:"中文译名待补";
  $("#infoEn").textContent=n.en||"";
  let st="已选择 / Selected";
  if(n.s===ROOT)st="职业起点 / Root";
  else if(!active.has(n.s))st=isAvail(n.s)?"可选择 / Available":"未连接 / Locked";
  $("#infoState").textContent=st;
  const desc=n.desc||"暂无可靠的预览版效果文本；节点名称和连线路径来自 Future update 树。\nNo reliable preview effect text is available here yet; the node name and path come from the Future update tree.";
  $("#infoDesc").textContent=desc;
  if(!boot)document.querySelector(".info-card").scrollIntoView({behavior:"smooth",block:"nearest"});
}
function setStatus(msg,type=""){
  const s=$("#status");s.textContent=msg;s.className="status"+(type?" "+type:"");
}
function applyZoom(){
  if(!CUR)return;
  const svg=$("#treeSvg"),scroll=$("#treeScroll");
  const vw=CUR.viewbox[2],vh=CUR.viewbox[3];
  const fit=Math.max(340,scroll.clientWidth-2);
  const width=fit*state.zoom;
  svg.style.width=width+"px";
  svg.style.height=(width*vh/vw)+"px";
}
function renderAll(resetScroll=false){
  renderClassbar();
  $("#buildName").value=state.name||"";
  $("#notes").value=state.notes||"";
  buildTree();
  if(resetScroll){$("#treeScroll").scrollTop=0;$("#treeScroll").scrollLeft=0;}
}
function exportData(){
  saveSelection();persist();
  return JSON.stringify({format:"Darktide-Future-Tree-BD-1",classKey:state.classKey,selected:state.selected,name:state.name,notes:state.notes},null,2);
}
function importData(txt){
  const x=JSON.parse(txt);
  if(x.format!=="Darktide-Future-Tree-BD-1")throw new Error("不是本规划器的 BD 数据 / Unsupported format");
  state.classKey=x.classKey||state.classKey;
  state.selected=x.selected||{};
  state.name=x.name||"";
  state.notes=x.notes||"";
  persist();renderAll(true);
}
function bind(){
  $("#resetBtn").onclick=()=>{
    if(confirm("重置当前职业的天赋？ / Reset this class tree?")){
      state.selected[state.classKey]=[];persist();renderAll(true);
    }
  };
  $("#saveBtn").onclick=()=>{
    saveSelection();persist();
    const b=$("#saveBtn"),old=b.innerHTML;b.innerHTML="已保存 ✓<br><small>Saved</small>";
    setTimeout(()=>b.innerHTML=old,900);
  };
  $("#zoomIn").onclick=()=>{state.zoom=Math.min(2.4,state.zoom*1.18);applyZoom();persist();};
  $("#zoomOut").onclick=()=>{state.zoom=Math.max(.72,state.zoom/1.18);applyZoom();persist();};
  $("#zoomFit").onclick=()=>{state.zoom=1;applyZoom();persist();$("#treeScroll").scrollLeft=0;};
  $("#buildName").oninput=()=>{state.name=$("#buildName").value;persist();};
  $("#notes").oninput=()=>{state.notes=$("#notes").value;persist();};
  $("#exportBtn").onclick=()=>{
    $("#codeBox").value=exportData();$("#dialogMsg").textContent="";
    if(typeof $("#codeDialog").showModal==="function")$("#codeDialog").showModal();
  };
  $("#importBtn").onclick=()=>{
    $("#codeBox").value="";$("#dialogMsg").textContent="粘贴 BD 数据后点击“载入” / Paste build data, then tap Load.";
    if(typeof $("#codeDialog").showModal==="function")$("#codeDialog").showModal();
  };
  $("#copyBtn").onclick=async()=>{
    const t=$("#codeBox").value;
    try{await navigator.clipboard.writeText(t);$("#dialogMsg").textContent="已复制 / Copied ✓";}
    catch(e){$("#codeBox").select();document.execCommand("copy");$("#dialogMsg").textContent="已复制 / Copied ✓";}
  };
  $("#loadBtn").onclick=()=>{
    try{importData($("#codeBox").value);$("#dialogMsg").textContent="载入成功 / Loaded ✓";setTimeout(()=>$("#codeDialog").close(),500);}
    catch(e){$("#dialogMsg").textContent=e.message;}
  };
  addEventListener("resize",()=>applyZoom());
}
try{
  if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));}
  if(!DATA||!Array.isArray(DATA.classes)||!DATA.classes.length)throw new Error("tree-data.js 未载入 / tree-data.js not loaded");
  load();bind();renderAll(true);
}catch(e){
  setStatus("天赋树启动失败 / Talent tree failed to start: "+e.message,"err");
}
})();