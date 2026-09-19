(()=>{
"use strict";
const DATA=window.DARKTIDE_DATA;
const STORE="darktide-cn-bd-v4";
let state={
  cls:"veteran",name:"",selected:{},
  melee:"",meleeInfo:"",ranged:"",rangedInfo:"",
  curios:[{value:""},{value:""},{value:""}],notes:""
};
const $=q=>document.querySelector(q);
const $$=q=>Array.from(document.querySelectorAll(q));
const key=t=>t[2]||t[1];
const isMajor=t=>["闪击","光环","主动技能","关键节点"].includes(t[0]);
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));

function readInputs(){
  state.name=$("#name").value;
  for(const id of ["melee","meleeInfo","ranged","rangedInfo","notes"]) state[id]=$("#"+id).value;
}
function writeInputs(){
  $("#name").value=state.name||"";
  for(const id of ["melee","meleeInfo","ranged","rangedInfo","notes"]) $("#"+id).value=state[id]||"";
}
function renderClasses(){
  const host=$("#classes"); host.innerHTML="";
  Object.entries(DATA.classes).forEach(([id,names])=>{
    const b=document.createElement("button");
    b.type="button";
    b.className=state.cls===id?"on":"";
    b.textContent=names[0]+" · "+names[1];
    b.onclick=()=>{readInputs();state.cls=id;renderAll();};
    host.appendChild(b);
  });
}
function renderTalents(){
  const host=$("#talents");
  const query=$("#search").value.trim().toLowerCase();
  host.innerHTML="";
  (DATA.talents[state.cls]||[])
    .filter(t=>!query||t.join(" ").toLowerCase().includes(query))
    .forEach(t=>{
      const k=key(t);
      const selected=!!(state.selected[state.cls]||{})[k];
      const b=document.createElement("button");
      b.type="button";
      b.className="talent"+(selected?" selected":"");
      b.innerHTML='<div class="tag">'+esc(t[0])+'</div><div class="cn">'+esc(t[1])+'</div><div class="en">'+esc(t[2])+'</div>';
      b.onclick=()=>toggleTalent(t);
      host.appendChild(b);
    });
}
function toggleTalent(t){
  state.selected[state.cls]=state.selected[state.cls]||{};
  const bucket=state.selected[state.cls],k=key(t);
  if(bucket[k]){
    delete bucket[k];
  }else{
    if(Object.keys(bucket).length>=30){alert("已经达到 30 点上限 / 30-point limit reached.");return;}
    if(isMajor(t)){
      (DATA.talents[state.cls]||[]).filter(x=>x[0]===t[0]).forEach(x=>delete bucket[key(x)]);
    }
    bucket[k]=t;
  }
  renderTalents();renderStats();renderSummary();
}
function renderStats(){
  const chosen=Object.values(state.selected[state.cls]||{});
  $("#pts").textContent=chosen.length;
  $("#major").textContent=chosen.filter(isMajor).length;
}
function renderCurios(){
  const host=$("#curios");host.innerHTML="";
  state.curios.forEach((c,i)=>{
    const wrap=document.createElement("div");
    wrap.className="curio";
    wrap.innerHTML='<b>珍品 '+(i+1)+' / Curio '+(i+1)+'</b><input data-i="'+i+'" value="'+esc(c.value||"")+'" placeholder="主属性、词条 / Main stat, perks">';
    host.appendChild(wrap);
  });
  host.querySelectorAll("input").forEach(el=>{
    el.oninput=()=>{state.curios[Number(el.dataset.i)].value=el.value;renderSummary();};
  });
}
function renderSummary(){
  readInputs();
  const chosen=Object.values(state.selected[state.cls]||{});
  const names=DATA.classes[state.cls];
  $("#summary").innerHTML=
    '<h2 class="summary-title">'+esc(state.name||"未命名 BD / Untitled Build")+'</h2>'+
    '<div class="summary-line"><b>'+esc(names[0])+' · '+esc(names[1])+'</b></div>'+
    '<div class="summary-line"><b>天赋 / Talents:</b> '+chosen.length+'/30<div class="chips">'+
    (chosen.length?chosen.map(t=>'<span class="chip">'+esc(t[1])+'<small>'+esc(t[2])+'</small></span>').join(""):'<span class="chip">尚未选择 / None selected</span>')+
    '</div></div>'+
    '<div class="summary-line"><b>近战 / Melee:</b> '+esc(state.melee||"—")+'<br><small>'+esc(state.meleeInfo||"")+'</small></div>'+
    '<div class="summary-line"><b>远程 / Ranged:</b> '+esc(state.ranged||"—")+'<br><small>'+esc(state.rangedInfo||"")+'</small></div>'+
    '<div class="summary-line"><b>珍品 / Curios:</b><br>'+state.curios.map((c,i)=>"#"+(i+1)+" "+esc(c.value||"—")).join("<br>")+'</div>';
}
function renderAll(){
  renderClasses();writeInputs();renderTalents();renderStats();renderCurios();renderSummary();
}
function save(){
  readInputs();
  try{
    localStorage.setItem(STORE,JSON.stringify(state));
    const b=$("#save"),old=b.innerHTML;
    b.innerHTML="已保存 ✓<small>Saved</small>";
    setTimeout(()=>b.innerHTML=old,1000);
  }catch(e){alert("当前浏览器无法本地保存 / Local storage is unavailable.");}
}
function load(){
  try{const raw=localStorage.getItem(STORE);if(raw) state={...state,...JSON.parse(raw)};}catch(e){}
}
function exportText(){
  readInputs();
  return JSON.stringify({format:"Darktide-CN-BD-4",...state},null,2);
}
function importText(text){
  const obj=JSON.parse(text);
  if(obj.format!=="Darktide-CN-BD-4") throw new Error("格式不匹配 / Unsupported build format");
  delete obj.format;
  state={...state,...obj};
  renderAll();save();
}
function openShare(){
  const d=$("#shareDialog");
  $("#shareBox").value=exportText();
  $("#shareStatus").textContent="";
  if(typeof d.showModal==="function") d.showModal();
  else{
    const text=prompt("复制导出内容；或粘贴导出的 JSON 进行导入。\nCopy export text, or paste exported JSON to import:",exportText());
    if(text&&text.trim().startsWith("{")) try{importText(text);}catch(e){alert(e.message);}
  }
}
function bind(){
  $$(".tabs button").forEach(b=>b.onclick=()=>{
    $$(".tabs button").forEach(x=>x.classList.toggle("on",x===b));
    $$("main section").forEach(s=>s.classList.toggle("on",s.id===b.dataset.tab));
    if(b.dataset.tab==="sum")renderSummary();
  });
  $("#search").oninput=renderTalents;
  $("#save").onclick=save;
  $("#reset").onclick=()=>{if(confirm("重置当前 BD？ / Reset this build?")){try{localStorage.removeItem(STORE);}catch(e){} location.reload();}};
  $("#share").onclick=openShare;
  $("#copyShare").onclick=async()=>{
    const text=$("#shareBox").value;
    try{await navigator.clipboard.writeText(text);$("#shareStatus").textContent="已复制 / Copied ✓";}
    catch(e){$("#shareBox").select();document.execCommand("copy");$("#shareStatus").textContent="已复制 / Copied ✓";}
  };
  $("#importShare").onclick=()=>{
    try{importText($("#shareBox").value);$("#shareStatus").textContent="导入成功 / Imported ✓";setTimeout(()=>$("#shareDialog").close(),600);}
    catch(e){$("#shareStatus").textContent=e.message;}
  };
  for(const id of ["name","melee","meleeInfo","ranged","rangedInfo","notes"]){
    $("#"+id).addEventListener("input",()=>{readInputs();if(id==="name")renderSummary();});
  }
}
function selfCheck(){
  const checks=[
    DATA&&Object.keys(DATA.classes||{}).length===7,
    (DATA.talents.veteran||[]).length>0,
    $("#classes").children.length===7,
    $("#talents").children.length>0
  ];
  if(checks.every(Boolean)) $("#runtimeWarning").classList.add("ok");
  else throw new Error("UI self-check failed");
}
window.addEventListener("error",e=>{
  const w=$("#runtimeWarning");
  if(w){w.classList.remove("ok");w.querySelector("b").textContent="网页脚本出错 / Script error";w.querySelector("span").textContent=String(e.message||"Unknown error");}
});
try{
  load();bind();renderAll();selfCheck();
  if("serviceWorker" in navigator) window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));
}catch(e){
  const w=$("#runtimeWarning");
  w.classList.remove("ok");
  w.querySelector("b").textContent="交互功能启动失败 / Interactive mode failed";
  w.querySelector("span").textContent=String(e.message||e);
}
})();