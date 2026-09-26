(()=>{
"use strict";

/*
  Interaction model is informed by LawsonMode/darktide-tree-planner,
  whose README explicitly permits reuse/modification of its original editor code.
  Tree data and game icon art are sourced from Games Lantern / Darktide game assets.
*/

const DATA=window.TREE_DATA;
let ICONS=(DATA&&DATA.icons)||window.TREE_ICONS||{};
const loadedIconPacks=new Set();
let iconsLoaded=Object.keys(ICONS).length>0;
const NS="http://www.w3.org/2000/svg";
const STORE="darktide-bilingual-editor-gl10";
const BASE_TREE_TOP=20;
const ICON_ART_SCALE=1.18; // Source talent art has transparent padding; zoom artwork inside the existing node clip.
let treeTop=BASE_TREE_TOP;

const QUERY=new URLSearchParams(location.search);
const DESKTOP_TEST=QUERY.get("desktoptest")==="1";
const MOBILE_TEST=QUERY.get("selftest")==="1"||QUERY.get("visual")==="popover";
const POINTER_MEDIA=matchMedia("(hover: hover) and (pointer: fine)");
function isDesktopInteraction(){
  return DESKTOP_TEST||(!MOBILE_TEST&&POINTER_MEDIA.matches);
}
function syncInputMode(){
  document.documentElement.classList.toggle("desktop-input",isDesktopInteraction());
  document.documentElement.classList.toggle("touch-input",!isDesktopInteraction());
}

const CAT={
  passive:{color:"#79b9c6",cn:"普通天赋",en:"Passive"},
  stat:{color:"#59616a",cn:"属性节点",en:"Stat"},
  blitz:{color:"#9edb70",cn:"闪击",en:"Blitz"},
  aura:{color:"#8bd178",cn:"光环",en:"Aura"},
  ability:{color:"#8ed9e7",cn:"主动技能",en:"Ability"},
  abilmod:{color:"#79a8c7",cn:"技能强化",en:"Ability modifier"},
  keystone:{color:"#d7b65a",cn:"关键节点",en:"Keystone"},
  keymod:{color:"#b89a52",cn:"关键强化",en:"Keystone modifier"},
  stimm:{color:"#a7c95b",cn:"兴奋剂强化",en:"Stimm upgrade"},
  root:{color:"#d5d8dc",cn:"职业节点",en:"Class node"}
};

const EXCLUSIVE=new Set(["blitz","aura","ability","keystone"]);

const VOCAB=[
  ["Toughness","韧性"],["Health","生命"],["Stamina","耐力"],["Damage Reduction","伤害减免"],
  ["Melee Attack Speed","近战攻击速度"],["Attack Speed","攻击速度"],["Movement Speed","移动速度"],
  ["Reload Speed","装填速度"],["Critical Chance","暴击率"],["Critical Hit","暴击"],
  ["Weakspot","弱点"],["Weak Spot","弱点"],["Melee Damage","近战伤害"],["Ranged Damage","远程伤害"],
  ["Power","威力"],["Strength","强度"],["Rending","撕裂"],["Brittleness","脆弱"],
  ["Bleeding","流血"],["Soulblaze","灵魂烈焰"],["Burning","燃烧"],["Toxin","毒素"],
  ["Coherency","协同范围"],["Cooldown","冷却"],["Combat Ability","战斗技能"],["Grenade","手雷"],
  ["Elite","精英"],["Specialist","专家"],["Monstrosity","巨兽"],["Carapace","甲壳装甲"],
  ["Flak Armoured","防弹装甲"],["Stagger","踉跄"],["Suppression","压制"],["Stealth","隐身"]
];

const TALENT_CN_OVERRIDES={};
const TALENT_NAME_CN_OVERRIDES={
  "Toughness Boost":"韧性提升",
  "Health Boost":"生命提升",
  "Stamina Boost":"耐力提升",
  "Damage Boost":"伤害提升",
  "Melee Damage Boost":"近战伤害提升",
  "Ranged Damage Boost":"远程伤害提升"
};
function cleanTalentName(name){
  return String(name||"")
    .replace(/\s+[A-F0-9]{8,}$/i,"")
    .replace(/[-_][A-F0-9]{8,}$/i,"")
    .trim();
}
function displayTalentEn(n){
  return cleanTalentName(n.en||"");
}
function displayTalentCn(n){
  const en=displayTalentEn(n);
  const raw=cleanTalentName(n.cn||"");
  if(TALENT_NAME_CN_OVERRIDES[en])return TALENT_NAME_CN_OVERRIDES[en];
  if(!raw||raw===en||/[A-F0-9]{8}$/i.test(raw))return en;
  return raw;
}
function stripGameMarkup(text){
  return String(text||"")
    .replace(/\{#color\([^}]*\)\}/gi,"")
    .replace(/\{#reset\(\)\}/gi,"")
    .replace(/\{#[^}]+\}/g,"")
    .replace(/\{[A-Za-z0-9_]+:%s\}/g,"")
    .trim();
}
function numericTokens(text){
  return new Set((String(text||"").match(/\d+(?:\.\d+)?%?/g)||[]).map(x=>x.replace(/\.0(?=%|$)/,"")));
}
function looksLikeEnhancedMismatch(n){
  const zh=String(n.descCn||"");
  const en=String(n.desc||"");
  if(!zh||!en)return false;
  if(/\{#(?:color|reset)/i.test(zh))return true;
  const zn=numericTokens(zh),enums=numericTokens(en);
  let extra=0;
  for(const x of zn)if(!enums.has(x))extra++;
  // Extra numeric mechanics usually means the Chinese text came from an enhanced-description layer.
  return extra>=2;
}
function descriptionPair(n){
  const enName=displayTalentEn(n);
  const fallbackEn=n.desc||(n.cat==="stat"
    ?"Stat node. Exact preview value is not available from the current data source."
    :"No reliable preview effect text is available for this node yet.");
  const baseEn=formatEnglishDescription(stripGameMarkup(fallbackEn));

  if(n.cat==="root"&&(n.mechanicsCn||n.mechanicsEn)){
    return {
      cn:"未来版本的职业基础属性与招牌被动请查看下方“机制核对”。",
      en:"See Mechanics check below for future class baseline stats and Iconic Passives.",
      source:"class-preview"
    };
  }
  if(TALENT_CN_OVERRIDES[enName]){
    return {cn:TALENT_CN_OVERRIDES[enName],en:baseEn,source:"curated-base"};
  }
  const source=n.descSource||"";
  const maintainedBase=n.descCn&&source!=="manual-reviewed"&&!looksLikeEnhancedMismatch(n);
  if(maintainedBase){
    return {
      cn:formatChineseDescription(stripGameMarkup(n.descCn)),
      en:baseEn,
      source:source||"base-aligned"
    };
  }
  if(n.advancedCn&&n.advancedEn){
    return {
      cn:formatChineseDescription(stripGameMarkup(n.advancedCn)),
      en:formatEnglishDescription(stripGameMarkup(n.advancedEn)),
      source:"paired-enhanced"
    };
  }
  if(n.descCn&&!looksLikeEnhancedMismatch(n)){
    return {
      cn:formatChineseDescription(stripGameMarkup(n.descCn)),
      en:baseEn,
      source:source||"base-aligned"
    };
  }
  if(n.cat==="stat"){
    const cn=displayTalentCn(n);
    return {
      cn:cn&&cn!==displayTalentEn(n)
        ?cn+"。具体数值暂未从预览数据源可靠读取。"
        :"该属性节点的具体数值暂未从预览数据源可靠读取。",
      en:baseEn,
      source:"stat-fallback"
    };
  }
  if(n.desc){
    return {
      cn:"暂无与英文原文可靠对应的简中说明，请参考下方英文原文。",
      en:baseEn,
      source:"english-only"
    };
  }
  return {
    cn:"暂无可靠的简中预览效果说明。",
    en:baseEn,
    source:"missing"
  };
}
function getChineseDescription(n){
  return descriptionPair(n).cn;
}

function formatChineseDescription(text){
  if(!text)return "";
  const lines=stripGameMarkup(text)
    .replace(/\r/g,"")
    .split(/\n+/)
    .map(x=>x.replace(/^\s*[•·▪●◦\-*]+\s*/,"").trim())
    .filter(Boolean);
  return lines
    .map(x=>x.replace(/\s+/g," ").trim())
    .join(" ")
    .replace(/\s*[•·▪●◦]\s*/g," ")
    .replace(/\s+([，。；：！？])/g,"$1")
    .replace(/([，。；：！？])\s+/g,"$1 ")
    .replace(/\s{2,}/g," ")
    .trim();
}
function formatEnglishDescription(text){
  return String(text||"")
    .replace(/\r/g,"")
    .replace(/\s*\n+\s*/g," ")
    .replace(/\s{2,}/g," ")
    .trim();
}

function translateEffectFallback(text){
  if(!text)return "暂无可靠的简中预览效果说明。";
  let s=String(text);
  const pairs=[
    [/Melee Weakspot Kills/gi,"近战弱点击杀"],
    [/Ranged Weakspot Kills/gi,"远程弱点击杀"],
    [/Weakspot Kills/gi,"弱点击杀"],
    [/Successful Melee Attacks/gi,"成功的近战攻击"],
    [/Successful Ranged Attacks/gi,"成功的远程攻击"],
    [/Melee Attacks/gi,"近战攻击"],
    [/Ranged Attacks/gi,"远程攻击"],
    [/Melee Damage/gi,"近战伤害"],
    [/Ranged Damage/gi,"远程伤害"],
    [/Toughness Damage Reduction/gi,"韧性伤害减免"],
    [/Damage Reduction/gi,"伤害减免"],
    [/Toughness/gi,"韧性"],
    [/Health/gi,"生命值"],
    [/Stamina/gi,"耐力"],
    [/Weakspot/gi,"弱点"],
    [/Critical Chance/gi,"暴击率"],
    [/Critical Hit/gi,"暴击"],
    [/Attack Speed/gi,"攻击速度"],
    [/Movement Speed/gi,"移动速度"],
    [/Reload Speed/gi,"装填速度"],
    [/Combat Ability/gi,"战斗技能"],
    [/Cooldown/gi,"冷却时间"],
    [/Coherency/gi,"协同范围"],
    [/Enemies/gi,"敌人"],
    [/Enemy/gi,"敌人"],
    [/Allies/gi,"盟友"],
    [/Damage/gi,"伤害"],
    [/Power/gi,"威力"],
    [/Strength/gi,"强度"],
    [/Rending/gi,"撕裂"],
    [/Brittleness/gi,"脆弱"],
    [/Staggered/gi,"已踉跄"],
    [/Stagger/gi,"踉跄"],
    [/Stealth/gi,"隐身"],
    [/seconds?/gi,"秒"],
    [/meters?/gi,"米"],
    [/restores?/gi,"恢复"],
    [/replenishes?/gi,"恢复"],
    [/increases?/gi,"提高"],
    [/reduces?/gi,"降低"],
    [/for /gi,"持续 "],
    [/ over /gi,"，在 "],
    [/ instantly/gi,"，立即生效"],
    [/ on /gi,"于"],
    [/ with /gi,"，使用"],
    [/ your /gi,"你的"],
    [/ you /gi,"你"],
    [/ all /gi,"所有"],
    [/ within /gi,"范围内"],
    [/ up to /gi,"，最多"],
    [/ per /gi,"每"],
  ];
  for(const [re,zh] of pairs)s=s.replace(re,zh);
  // If the fallback is still mostly English, mark it clearly as an automatic aid.
  const latin=(s.match(/[A-Za-z]/g)||[]).length;
  const total=Math.max(1,s.replace(/\s/g,"").length);
  if(latin/total>.32)return "自动辅助翻译： "+s;
  return s;
}

const GEAR_GUIDE={
  veteran:{
    melee:["Maccabian Mk IV Duelling Sword","Scandar Mk III Power Sword"],
    ranged:["M35 Magnacore Mk II Plasma Gun","Accatran Mk XIV Recon Lasgun"],
    curios:"参考 / Reference: 3× 韧性 Toughness；词条优先韧性回复、技能冷却、枪手减伤 / Toughness Regen, Ability Regen, Gunner DR."
  },
  zealot:{
    melee:["Maccabian Mk IV Duelling Sword","Munitorum Mk X Relic Blade"],
    ranged:["Artemia Mk III Purgation Flamer","Zarona Mk IIa Quickdraw Stub Revolver"],
    curios:"参考 / Reference: 2–3× 韧性 Toughness；可混 1× 生命 Health。"
  },
  psyker:{
    melee:["Maccabian Mk IV Duelling Sword","Covenant Mk VI Blaze Force Greatsword"],
    ranged:["Rifthaven Mk II Inferno Force Staff","Equinox Mk IV Voidstrike Force Staff"],
    curios:"参考 / Reference: 韧性 Toughness + 技能冷却 Ability Regen；按玩法补生命 / Health."
  },
  ogryn:{
    melee:["Karsolas Mk II Delver's Pickaxe","Brute-Brainer Mk XIX Latrine Shovel"],
    ranged:["Lorenz Mk VI Rumbler","Foe-Rend Mk V Ripper Gun"],
    curios:"参考 / Reference: 生命 Health 与韧性 Toughness 混搭；枪手减伤 / Gunner DR."
  },
  arbites:{
    melee:["Branx Mk III Arbites Shock Maul","Branx Mk VI Shock Maul & Suppression Shield"],
    ranged:["Exaction Mk VIII Exterminator Shotgun","Godwyn-Branx Mk IV Bolt Pistol"],
    curios:"参考 / Reference: 2× 韧性 Toughness + 1× 生命 Health；枪手减伤与技能冷却。"
  },
  skitarii:{
    melee:["Branx Mk XI Paired Transonic Blades","Branx Mk III Arc Maul"],
    ranged:["Branx Mk CV Galvanic Rifle","Branx Mk XI Phosphor Blast Pistol"],
    curios:"参考 / Reference: 韧性 Toughness 为主；技能冷却、韧性回复、枪手减伤。"
  },
  hivescum:{
    melee:["Improvised Mk I Shivs","Enginseer's Mk VI Crowbar"],
    ranged:["Branx MkVIII Dual Stub Pistols","Branx MkIII Dual Autopistols"],
    curios:"参考 / Reference: 韧性 Toughness 为主；技能冷却、韧性回复、耐力 / Stamina."
  }
};

const WF={
  combatBlade:["Catachan Mk III Combat Blade","Catachan Mk VI Combat Blade"],
  duellingSword:["Maccabian Mk IV Duelling Sword","Maccabian Mk II Duelling Sword","Maccabian Mk V Duelling Sword"],
  devilsClaw:['Catachan Mk VII "Devil\'s Claw" Sword','Catachan Mk IV "Devil\'s Claw" Sword','Catachan Mk I "Devil\'s Claw" Sword'],
  tacticalAxe:["Atrox Mk VII Tactical Axe","Atrox Mk II Tactical Axe","Atrox Mk IV Tactical Axe"],
  chainsword:["Cadia Mk IV Assault Chainsword","Cadia Mk XIIIg Assault Chainsword"],
  combatAxe:["Rashad Mk III Combat Axe","Antax Mk V Combat Axe","Achlys Mk VIII Combat Axe"],
  chainaxe:["Orestes Mk IV Assault Chainaxe","Orestes Mk XII Assault Chainaxe"],
  shockMaul:["Munitorum Mk III Shock Maul","Agni Mk Ia Shock Maul"],
  heavySword:["Turtolsky Mk VII Heavy Sword","Turtolsky Mk VI Heavy Sword","Turtolsky Mk IX Heavy Sword"],
  crusher:["Krourk Mk VII Crusher","Indignatus Mk IVe Crusher"],
  powerFalchion:["Lawbringer Mk IIb Power Falchion","Aridin Mk I Power Falchion"],
  recon:["Accatran Mk XIV Recon Lasgun","Accatran Mk VIc Recon Lasgun","Accatran Mk XII Recon Lasgun"],
  combatShotgun:["Zarona Mk VI Combat Shotgun","Agripinaa Mk VII Combat Shotgun","Accatran Mk IX Combat Shotgun"],
  boltgun:["Locke Mk III Spearhead Boltgun","Locke Mk IIb Spearhead Boltgun"],
  vigilant:["Agripinaa Mk IX Vigilant Autogun","Graia Mk VII Vigilant Autogun","Columnus Mk III Vigilant Autogun"],
  doubleBarrel:["Crucis Mk XI Double-Barrelled Shotgun","Krourk Mk IV Double-Barrelled Shotgun"],
  boltPistol:["Godwyn-Branx Mk IV Bolt Pistol","Godwyn-Branx Mk VI Bolt Pistol"],
  infantryAutogun:["Columnus Mk VIII Infantry Autogun","Vraks Mk V Infantry Autogun","Agripinaa Mk I Infantry Autogun"],
  huntsman:["Accatran Mk III Huntsman's Shotgun"],
  infantryLasgun:["Kantrael Mk IIb Infantry Lasgun","Kantrael Mk IX Infantry Lasgun","Kantrael Mk VII Infantry Lasgun"],
  braced:["Agripinaa Mk VIII Braced Autogun","Vraks Mk II Braced Autogun","Graia Mk IV Braced Autogun"],
  plasma:["M35 Magnacore Mk III Plasma Gun","M35 Magnacore Mk II Plasma Gun"],
  shredder:["Ius Mk IV Shredder Autopistol"],
  revolver:["Zarona Mk IIa Quickdraw Stub Revolver","Agripinaa Mk XIV Quickdraw Stub Revolver"],
  heavyLaspistol:["Kantrael Mk X Heavy Laspistol","Accatran MG Mk II Heavy Laspistol"]
};
const EQUIPMENT_DB={
  veteran:{
    melee:[
      "Munitorum Mk I Sapper Shovel","Munitorum Mk VII Sapper Shovel","Munitorum Mk III Sapper Shovel",
      "Scandar Mk III Power Sword","Achlys Mk VI Power Sword",
      ...WF.combatBlade,...WF.duellingSword,...WF.devilsClaw,...WF.tacticalAxe,...WF.chainsword,
      ...WF.combatAxe,...WF.chainaxe,...WF.shockMaul,...WF.powerFalchion,...WF.heavySword
    ],
    ranged:[
      "Lucius Mk IV Helbore Lasgun","Lucius MK V Helbore Lasgun","Lucius MK IIIa Helbore Lasgun",
      ...WF.recon,...WF.combatShotgun,...WF.boltgun,...WF.vigilant,...WF.doubleBarrel,...WF.boltPistol,
      ...WF.infantryAutogun,...WF.huntsman,...WF.infantryLasgun,...WF.braced,...WF.plasma,...WF.shredder,
      ...WF.revolver,...WF.heavyLaspistol
    ]
  },
  zealot:{
    melee:[
      "Crucis Mk II Thunder Hammer","Ironhelm Mk IV Thunder Hammer",
      "Munitorum Mk II Relic Blade","Munitorum Mk X Relic Blade",
      "Tigrus Mk III Heavy Eviscerator","Tigrus Mk XV Heavy Eviscerator",
      ...WF.combatBlade,...WF.duellingSword,...WF.crusher,...WF.devilsClaw,...WF.tacticalAxe,...WF.chainsword,
      ...WF.combatAxe,...WF.chainaxe,...WF.shockMaul,...WF.heavySword
    ],
    ranged:[
      "Artemia Mk III Purgation Flamer",
      ...WF.recon,...WF.combatShotgun,...WF.boltgun,...WF.vigilant,...WF.doubleBarrel,...WF.boltPistol,
      ...WF.infantryAutogun,...WF.huntsman,...WF.infantryLasgun,...WF.braced,...WF.shredder,...WF.revolver,...WF.heavyLaspistol
    ]
  },
  psyker:{
    melee:[
      "Obscurus Mk II Blaze Force Sword","Deimos Mk IV Blaze Force Sword","Illisi Mk V Blaze Force Sword",
      "Covenant Mk VIII Blaze Force Greatsword","Covenant Mk VI Blaze Force Greatsword",
      ...WF.combatBlade,...WF.duellingSword,...WF.devilsClaw,...WF.tacticalAxe,...WF.chainsword,
      ...WF.combatAxe,...WF.chainaxe,...WF.shockMaul,...WF.heavySword
    ],
    ranged:[
      "Rifthaven Mk II Inferno Force Staff","Equinox Mk III Voidblast Force Staff",
      "Nomanus Mk VI Electrokinetic Force Staff","Equinox Mk IV Voidstrike Force Staff",
      ...WF.recon,...WF.combatShotgun,...WF.vigilant,...WF.doubleBarrel,...WF.boltPistol,...WF.infantryAutogun,
      ...WF.huntsman,...WF.infantryLasgun,...WF.braced,...WF.shredder,...WF.revolver,...WF.heavyLaspistol
    ]
  },
  arbites:{
    melee:[
      "Branx Mk XI Shock Maul and Suppression Shield","Branx Mk VI Shock Maul and Suppression Shield",
      "Judgement Mk IV Subductor Shotpistol and Riot Shield","Branx Mk III Arbites Shock Maul",
      ...WF.crusher,...WF.tacticalAxe,...WF.chainsword,...WF.combatAxe,...WF.shockMaul
    ],
    ranged:[
      "Exaction Mk III Exterminator Shotgun","Exaction Mk VIII Exterminator Shotgun",
      ...WF.combatShotgun,...WF.boltgun,...WF.vigilant,...WF.doubleBarrel,...WF.boltPistol,
      ...WF.infantryAutogun,...WF.braced,...WF.shredder,...WF.revolver
    ]
  },
  skitarii:{
    melee:[
      "Branx Mk VI Mechanicus Power Sword","Branx Mk XI Paired Transonic Blades","Branx Mk III Arc Maul",
      ...WF.combatBlade,...WF.devilsClaw,...WF.chainsword,...WF.shockMaul,...WF.powerFalchion
    ],
    ranged:[
      "Branx Mk CV Galvanic Rifle","Branx Mk XI Phosphor Blast Pistol","Branx Mk IV Arc Rifle",
      ...WF.vigilant,...WF.infantryAutogun,...WF.braced,...WF.plasma,...WF.shredder,...WF.revolver,...WF.heavyLaspistol
    ]
  },
  hivescum:{
    melee:[
      "Enginseer's Mk VI Crowbar","Chirurgeon's Mk IV Bone Saw","Improvised Mk III Shivs","Improvised Mk I Shivs",
      ...WF.combatBlade,...WF.devilsClaw,...WF.tacticalAxe,...WF.chainsword,...WF.combatAxe,...WF.chainaxe,...WF.heavySword
    ],
    ranged:[
      "Branx MkVIII Dual Stub Pistols","Branx MkIII Dual Autopistols","Branx MkVI Needle Pistol","Branx MKII Needle Pistol",
      ...WF.combatShotgun,...WF.vigilant,...WF.doubleBarrel,...WF.boltPistol,...WF.infantryAutogun,
      ...WF.huntsman,...WF.braced,...WF.shredder,...WF.revolver
    ]
  },
  ogryn:{
    melee:[
      '"Brunt Special" Mk I Bully Club','"Brunt\'s Pride" Mk II Bully Club','"Brunt\'s Basher" Mk IIIb Bully Club',
      "Gromm Mk I & Mk V Battle Maul & Slab Shield","Orox Mk II & Mk III Battle Maul & Slab Shield",
      "Brute-Brainer Mk III Latrine Shovel","Brute-Brainer Mk V Latrine Shovel","Brute-Brainer Mk XIX Latrine Shovel",
      "Borovian Mk III Delver's Pickaxe","Karsolas Mk II Delver's Pickaxe","Branx Mk Ia Delver's Pickaxe",
      "Achlys Mk I Power Maul","Krourk Mk IIa Cruncher","Bull Butcher Mk III Cleaver","Krourk Mk IV Cleaver","Krourk Mk VI Cleaver"
    ],
    ranged:[
      "Lorenz Mk V Kickback","Foe-Rend Mk II Ripper Gun","Foe-Rend Mk VI Ripper Gun","Foe-Rend Mk V Ripper Gun",
      "Krourk Mk V Twin-Linked Heavy Stubber","Achlys Mk VII Twin-Linked Heavy Stubber","Gorgonum Mk IV Twin-Linked Heavy Stubber",
      "Blastoom Mk III Grenadier Gauntlet","Gorgonum Mk IIIa Heavy Stubber","Achlys Mk II Heavy Stubber","Krourk Mk IIa Heavy Stubber",
      "Lorenz Mk VII Thugshot","Lorenz Mk VI Rumbler"
    ]
  }
};
const CURIO_TYPES=[
  "Blessed Bullet","Gilded Inquisitorial Rosette","Gilded Mandible","Guardian Nocturnus","Guardian of the Hateful",
  "Guardian of the Lost","Herald's Seal","Laurel of the Just","Laurel of the Righteous","Mechanicus Icon Illustrious",
  "Obsidiax-Sheathed Bullet","Redeemer's Gilded Hand","Saintly Fragment","Scrap of Scripture","Stalwart's Mandible"
];
const CURIO_MAINS=["+1 Wound(s)","+1-3 Max Stamina","+13-17% Toughness","+17-21% Max Health"];
const CURIO_PERKS=[
  "+1-4% Combat Ability Regeneration","+2-10% Experience","+2-5% Health","+2-5% Toughness",
  "+4-10% Ordo Dockets (Mission Rewards)","+4-10% Revive Speed (Ally)",
  "+5-20% chance of Curio as Mission Reward (Instead of Weapon)","+5-20% Corruption Resistance (Grimoires)",
  "+5-20% Damage Resistance (Bombers)","+5-20% Damage Resistance (Gunners)",
  "+5-20% Damage Resistance (Mutants)","+5-20% Damage Resistance (Pox Hounds)",
  "+5-20% Damage Resistance (Snipers)","+5-20% Damage Resistance (Tox Flamers)",
  "+6-12% Block Efficiency","+6-12% Stamina Regeneration","+6-15% Corruption Resistance",
  "+7.5-30% Toughness Regeneration Speed","6-15% Sprint Efficiency"
];
function uniqueStrings(arr){
  return [...new Set((arr||[]).filter(Boolean))];
}

let state={
  patch:"future",
  classKey:"veteran",
  selected:{},
  loadouts:{},
  name:"",
  notes:"",
  zoom:1,
  builds:[],
  activeBuildId:""
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
let actionHistory=[];
let toastTimer=null;

const $=q=>document.querySelector(q);
const VISUAL_POPOVER_TEST=new URLSearchParams(location.search).get("visual")==="popover";

const LOADOUT_FIELDS=[
  "meleeWeapon","meleeBlessing1","meleeBlessing2","meleePerk1","meleePerk2",
  "rangedWeapon","rangedBlessing1","rangedBlessing2","rangedPerk1","rangedPerk2",
  "curio1Type","curio1Main","curio1Perks",
  "curio2Type","curio2Main","curio2Perks",
  "curio3Type","curio3Main","curio3Perks"
];
function blankLoadout(){
  return Object.fromEntries(LOADOUT_FIELDS.map(k=>[k,""]));
}
function baseClassKey(k=state.classKey){
  const c=classByKey(k);
  return c.parent||c.key;
}
function currentLoadout(){
  state.loadouts=state.loadouts||{};
  const key=baseClassKey();
  state.loadouts[key]={...blankLoadout(),...(state.loadouts[key]||{})};
  return state.loadouts[key];
}
function captureLoadout(){
  if(!document.getElementById("meleeWeapon"))return;
  const lo=currentLoadout();
  for(const id of LOADOUT_FIELDS){
    const el=document.getElementById(id);
    if(el)lo[id]=el.value||"";
  }
}
function applyLoadout(){
  const lo=currentLoadout();
  for(const id of LOADOUT_FIELDS){
    const el=document.getElementById(id);
    if(el)el.value=lo[id]||"";
  }
}
function renderGearSuggestions(){
  const guide=GEAR_GUIDE[baseClassKey()]||{melee:[],ranged:[],curios:""};
  if($("#curioHint"))$("#curioHint").textContent=(guide.curios||"")+" 珍品类型仅用于记录外观，不影响主属性或词条。可输入关键词搜索，也可点右侧箭头浏览完整列表。 / Curio type is cosmetic; search by typing or open the full list.";
  refreshOpenPickers();
}
function weaponOptions(slot){
  const key=baseClassKey();
  const guide=GEAR_GUIDE[key]||{melee:[],ranged:[]};
  const all=(EQUIPMENT_DB[key]&&EQUIPMENT_DB[key][slot])||[];
  const recommended=guide[slot]||[];
  return uniqueStrings([...recommended,...all]).map(label=>({label,recommended:recommended.includes(label)}));
}

function makeBuildId(){
  if(globalThis.crypto&&crypto.randomUUID)return crypto.randomUUID();
  return "bd-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,9);
}
function cloneJson(v){
  return JSON.parse(JSON.stringify(v??null));
}
function snapshotCurrentBuild(id=state.activeBuildId||makeBuildId()){
  return {
    id,
    name:state.name||"",
    notes:state.notes||"",
    patch:state.patch==="live"?"live":"future",
    classKey:state.classKey||"veteran",
    selected:cloneJson(state.selected||{}),
    loadouts:cloneJson(state.loadouts||{}),
    zoom:Number.isFinite(state.zoom)?state.zoom:1,
    updatedAt:Date.now()
  };
}
function applyBuildSnapshot(build){
  if(!build)return;
  state.name=build.name||"";
  state.notes=build.notes||"";
  state.patch=build.patch==="live"?"live":"future";
  state.classKey=build.classKey||"veteran";
  state.selected=cloneJson(build.selected||{});
  state.loadouts=cloneJson(build.loadouts||{});
  state.zoom=Number.isFinite(build.zoom)?build.zoom:1;
}
function blankBuild(){
  return {
    id:makeBuildId(),
    name:"新 BD / New Build",
    notes:"",
    patch:state.patch==="live"?"live":"future",
    classKey:baseClassKey()||"veteran",
    selected:{},
    loadouts:{},
    zoom:1,
    updatedAt:Date.now()
  };
}
function syncActiveBuild(){
  state.builds=Array.isArray(state.builds)?state.builds:[];
  if(!state.activeBuildId)return;
  const i=state.builds.findIndex(b=>b&&b.id===state.activeBuildId);
  if(i>=0)state.builds[i]={...state.builds[i],...snapshotCurrentBuild(state.activeBuildId)};
}
function ensureBuildLibrary(){
  state.builds=Array.isArray(state.builds)?state.builds.filter(Boolean):[];
  if(!state.builds.length){
    const first=snapshotCurrentBuild(makeBuildId());
    if(!first.name)first.name="我的 BD 1 / My Build 1";
    state.builds=[first];
    state.activeBuildId=first.id;
    return;
  }
  let active=state.builds.find(b=>b.id===state.activeBuildId);
  if(!active){
    active=state.builds[0];
    state.activeBuildId=active.id;
  }
  applyBuildSnapshot(active);
}
function writeStorage(){
  try{localStorage.setItem(STORE,JSON.stringify(state));}catch(_){}
}
function classLabelForBuild(build){
  const list=build.patch==="live"&&Array.isArray(DATA.liveClasses)?DATA.liveClasses:DATA.classes;
  const c=(list||[]).find(x=>x.key===build.classKey)||(list||[]).find(x=>!x.parent);
  return c?(c.cn+" · "+c.name):build.classKey;
}
function renderBuildLibrary(){
  const select=$("#buildSelect");
  if(!select)return;
  const current=state.activeBuildId;
  select.innerHTML="";
  for(const b of state.builds||[]){
    const opt=document.createElement("option");
    opt.value=b.id;
    const title=(b.name||"未命名 BD / Untitled").trim();
    opt.textContent=title+"  ·  "+classLabelForBuild(b)+"  ·  "+(b.patch==="live"?"LIVE":"FUTURE");
    select.appendChild(opt);
  }
  select.value=current||"";
  const hint=$("#buildLibraryHint");
  if(hint)hint.textContent=(state.builds?.length||0)+" 套 BD 已保存在本机浏览器 · 当前修改自动保存 / "+(state.builds?.length||0)+" builds saved locally · autosave on";
}
function switchSavedBuild(id){
  if(!id||id===state.activeBuildId)return;
  saveSelection();
  persist();
  const next=(state.builds||[]).find(b=>b.id===id);
  if(!next)return;
  state.activeBuildId=id;
  applyBuildSnapshot(next);
  clearHistory();
  hideInfo(false);
  renderAll(true);
  writeStorage();
  queueCurrentIconPack();
}
function createSavedBuild(copyCurrent=false){
  saveSelection();
  persist();
  let next;
  if(copyCurrent){
    next=snapshotCurrentBuild(makeBuildId());
    next.name=((state.name||"未命名 BD / Untitled").trim()+" · 副本 / Copy");
  }else{
    next=blankBuild();
  }
  state.builds.push(next);
  state.activeBuildId=next.id;
  applyBuildSnapshot(next);
  clearHistory();
  renderAll(true);
  writeStorage();
  queueCurrentIconPack();
  notify(copyCurrent?"已复制为新 BD / Build duplicated":"已新建空白 BD / New build created");
}
function deleteSavedBuild(){
  const builds=state.builds||[];
  const i=builds.findIndex(b=>b.id===state.activeBuildId);
  if(i<0)return;
  const title=(builds[i].name||"未命名 BD / Untitled").trim();
  if(!confirm("删除“"+title+"”？此操作只删除本机保存的数据。\nDelete this locally saved build?"))return;
  builds.splice(i,1);
  if(!builds.length)builds.push(blankBuild());
  const next=builds[Math.min(i,builds.length-1)];
  state.activeBuildId=next.id;
  applyBuildSnapshot(next);
  clearHistory();
  renderAll(true);
  writeStorage();
  queueCurrentIconPack();
  notify("已删除 BD / Build deleted");
}

const pickerRegistry=[];
function normalizePickerItem(item){
  return typeof item==="string"?{label:item,recommended:false}:item;
}
function pickerQuery(input,multi,allLabels){
  const raw=input.value||"";
  if(!multi)return raw.trim();
  const bits=raw.split("|");
  const last=(bits[bits.length-1]||"").trim();
  return allLabels.includes(last)?"":last;
}
function setupSearchPicker(id,provider,{multi=false,max=3}={}){
  const input=document.getElementById(id);
  if(!input||input.dataset.pickerReady==="1")return;
  input.dataset.pickerReady="1";
  const host=document.createElement("div");
  host.className="picker-host";
  input.parentNode.insertBefore(host,input);
  host.appendChild(input);
  const toggle=document.createElement("button");
  toggle.type="button";
  toggle.className="picker-toggle";
  toggle.setAttribute("aria-label","展开选择 / Open choices");
  toggle.textContent="⌄";
  const menu=document.createElement("div");
  menu.className="picker-menu";
  menu.hidden=true;
  host.appendChild(toggle);
  host.appendChild(menu);
  let activeIndex=-1;

  function items(){
    return uniqueStrings(provider().map(x=>normalizePickerItem(x).label)).map(label=>{
      const original=provider().map(normalizePickerItem).find(x=>x.label===label);
      return original||{label,recommended:false};
    });
  }
  function renderMenu(forceAll=false){
    const all=items();
    const labels=all.map(x=>x.label);
    const q=(forceAll?"":pickerQuery(input,multi,labels)).toLowerCase();
    const selected=multi?(input.value||"").split("|").map(x=>x.trim()).filter(x=>labels.includes(x)):[];
    const matches=all.filter(x=>!selected.includes(x.label)&&(!q||x.label.toLowerCase().includes(q))).slice(0,40);
    menu.innerHTML="";
    activeIndex=-1;
    if(!matches.length){
      const empty=document.createElement("div");
      empty.className="picker-empty";
      empty.textContent="没有匹配项；也可以保留手动输入 / No match — custom text is allowed";
      menu.appendChild(empty);
    }else{
      for(const item of matches){
        const b=document.createElement("button");
        b.type="button";
        b.className="picker-option"+(item.recommended?" recommended":"");
        b.textContent=item.label;
        b.onclick=()=>{
          if(multi){
            const allLabels=all.map(x=>x.label);
            let parts=(input.value||"").split("|").map(x=>x.trim()).filter(Boolean);
            if(parts.length&& !allLabels.includes(parts[parts.length-1]))parts.pop();
            parts=parts.filter(x=>allLabels.includes(x));
            if(!parts.includes(item.label)&&parts.length<max)parts.push(item.label);
            input.value=parts.join(" | ")+(parts.length<max?" | ":"");
          }else{
            input.value=item.label;
          }
          input.dispatchEvent(new Event("input",{bubbles:true}));
          if(multi&&((input.value||"").split("|").map(x=>x.trim()).filter(Boolean).length<max)){
            input.focus();
            renderMenu(true);
          }else{
            menu.hidden=true;
          }
        };
        menu.appendChild(b);
      }
    }
    menu.hidden=false;
  }
  function setActive(next){
    const buttons=[...menu.querySelectorAll(".picker-option")];
    if(!buttons.length)return;
    activeIndex=Math.max(0,Math.min(buttons.length-1,next));
    buttons.forEach((b,i)=>b.classList.toggle("active",i===activeIndex));
    buttons[activeIndex].scrollIntoView({block:"nearest"});
  }
  input.addEventListener("focus",()=>renderMenu(false));
  input.addEventListener("input",()=>renderMenu(false));
  input.addEventListener("keydown",e=>{
    if(e.key==="ArrowDown"){
      e.preventDefault();
      if(menu.hidden)renderMenu(false);
      setActive(activeIndex+1);
    }else if(e.key==="ArrowUp"){
      e.preventDefault();
      setActive(activeIndex-1);
    }else if(e.key==="Enter"&&!menu.hidden&&activeIndex>=0){
      e.preventDefault();
      const buttons=[...menu.querySelectorAll(".picker-option")];
      buttons[activeIndex]?.click();
    }else if(e.key==="Escape"){
      menu.hidden=true;
    }
  });
  toggle.onclick=()=>menu.hidden?renderMenu(true):(menu.hidden=true);
  host.addEventListener("focusout",()=>setTimeout(()=>{
    if(!host.contains(document.activeElement))menu.hidden=true;
  },80));
  pickerRegistry.push({input,menu,renderMenu});
}
function setupEquipmentPickers(){
  setupSearchPicker("meleeWeapon",()=>weaponOptions("melee"));
  setupSearchPicker("rangedWeapon",()=>weaponOptions("ranged"));
  for(let i=1;i<=3;i++){
    setupSearchPicker("curio"+i+"Type",()=>CURIO_TYPES);
    setupSearchPicker("curio"+i+"Main",()=>CURIO_MAINS);
    setupSearchPicker("curio"+i+"Perks",()=>CURIO_PERKS,{multi:true,max:3});
  }
}
function refreshOpenPickers(){
  for(const p of pickerRegistry){
    if(!p.menu.hidden)p.renderMenu(false);
  }
}

function load(){
  try{
    const raw=localStorage.getItem(STORE);
    if(raw) state={...state,...JSON.parse(raw)};
  }catch(_){}
  ensureBuildLibrary();
}
function persist(){
  const name=$("#buildName");
  const notes=$("#notes");
  if(name) state.name=name.value||"";
  if(notes) state.notes=notes.value||"";
  captureLoadout();
  syncActiveBuild();
  writeStorage();
}
function treeList(){
  if(state.patch==="live"&&Array.isArray(DATA.liveClasses)&&DATA.liveClasses.length)return DATA.liveClasses;
  return DATA.classes;
}
function classByKey(k){
  const list=treeList();
  return list.find(c=>c.key===k)||list[0];
}
function selectionKey(k=state.classKey){
  return state.patch+":"+k;
}
function patchLabel(){
  return state.patch==="live"?(DATA.liveVersion||"Live patch"):(DATA.version||"Future update");
}
function radius(n){
  if(n.cat==="keystone")return 42;
  if(n.cat==="ability")return 41;
  if(n.cat==="blitz"||n.cat==="aura")return 38;
  if(n.cat==="root")return 39;
  if(n.cat==="stat")return 12;
  if(n.cat==="keymod"||n.cat==="abilmod")return 30;
  return 34;
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
  const ir=Math.max(5,r-3);
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
function loadTalentIconsForClass(base=baseClassKey()){
  if(!base)return;
  if(loadedIconPacks.has(base))return;
  const attr=CSS.escape(base);
  if(document.querySelector('script[data-tree-icon-pack="'+attr+'"]'))return;
  const s=document.createElement("script");
  s.src="./tree-icons-"+encodeURIComponent(base)+".js?v=gl31";
  s.async=true;
  s.dataset.treeIconPack=base;
  s.onload=()=>{
    ICONS=window.TREE_ICONS||ICONS||{};
    loadedIconPacks.add(base);
    iconsLoaded=Object.keys(ICONS).length>0;
    document.body.dataset.iconsLoaded=String(iconsLoaded);
    document.body.dataset.iconPack=base;
    renderClassbar();
    if(CUR&&baseClassKey()===base){
      const vp=$("#treeViewport");
      const keepLeft=vp?.scrollLeft||0;
      buildTree();
      requestAnimationFrame(()=>{
        const current=$("#treeViewport");
        if(current)current.scrollLeft=keepLeft;
      });
    }
  };
  s.onerror=()=>{
    document.body.dataset.iconsLoaded="false";
    document.body.dataset.iconPackError=base;
  };
  document.head.appendChild(s);
}

function queueCurrentIconPack(){
  const base=baseClassKey();
  if(!base||loadedIconPacks.has(base))return;
  const go=()=>loadTalentIconsForClass(base);
  if("requestIdleCallback" in window)requestIdleCallback(go,{timeout:500});
  else setTimeout(go,80);
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
  if(CUR) state.selected[selectionKey(CUR.key)]=[...active].filter(s=>s!==ROOT);
}
function restoreSelection(){
  const key=selectionKey(CUR.key);
  if(state.patch==="future"&&!state.selected[key]&&state.selected[CUR.key]){
    state.selected[key]=state.selected[CUR.key];
  }
  const wanted=new Set(state.selected[key]||[]);
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
  const selectedBase=baseClassKey();
  for(const c of treeList().filter(x=>!x.parent)){
    const b=document.createElement("button");
    b.type="button";
    b.className=c.key===selectedBase?"on":"";
    const root=c.nodes.find(n=>n.cat==="root");
    const icon=root&&ICONS[root.s]?'<img src="'+ICONS[root.s]+'" alt="">':"";
    b.innerHTML=icon+`<span>${c.cn} · ${c.name}</span>`;
    b.onclick=()=>{
      saveSelection();
      persist();
      state.classKey=c.key;
      syncActiveBuild();
      writeStorage();
      hotSlug=null;
      clearHistory();
      renderAll(true);
      renderBuildLibrary();
      queueCurrentIconPack();
    };
    bar.appendChild(b);
  }
}
function renderPatchControls(){
  const future=$("#futurePatchBtn"),live=$("#livePatchBtn");
  if(future)future.classList.toggle("active",state.patch==="future");
  if(live)live.classList.toggle("active",state.patch==="live");
  const note=document.querySelector(".patch-note");
  if(note)note.textContent=state.patch==="live"
    ?"当前使用正式服天赋树；切换版本不会覆盖另一版本的加点。 / Live tree selected; each patch keeps its own build."
    :"当前使用未来更新天赋树；切换版本不会覆盖正式服加点。 / Future tree selected; each patch keeps its own build.";
}
function switchPatch(next){
  if(next===state.patch)return;
  saveSelection();
  persist();
  const oldKey=state.classKey;
  state.patch=next;
  const list=treeList();
  state.classKey=list.some(c=>c.key===oldKey)?oldKey:(list.find(c=>!c.parent)?.key||list[0].key);
  hotSlug=null;
  clearHistory();
  renderAll(true);
  queueCurrentIconPack();
  persist();
}
function renderSubtreeBar(){
  const host=$("#subtreeStrip");
  if(!host)return;
  const base=baseClassKey();
  if(base!=="hivescum"){
    host.className="subtree-strip";
    host.innerHTML="";
    return;
  }
  const choices=[
    treeList().find(c=>c.key==="hivescum"),
    treeList().find(c=>c.key==="hivescum-stimm")
  ].filter(Boolean);
  host.className="subtree-strip show";
  host.innerHTML="";
  for(const c of choices){
    const b=document.createElement("button");
    b.type="button";
    b.className=c.key===state.classKey?"on":"";
    b.textContent=c.key==="hivescum"?"天赋树 · Talent Tree":"兴奋剂实验室 · Stimm Lab";
    b.onclick=()=>{
      saveSelection();
      persist();
      state.classKey=c.key;
      syncActiveBuild();
      writeStorage();
      hotSlug=null;
      clearHistory();
      renderAll(true);
      renderBuildLibrary();
      queueCurrentIconPack();
    };
    host.appendChild(b);
  }
}
function renderNode(svg,defs,n){
  const r=radius(n);
  const g=createSvg("g",{class:"node"+(n.cat==="stat"?" stat":""),"data-s":n.s});
  const hit=createSvg("circle",{cx:n.x,cy:n.y,r:Math.max(24,r+10),class:"hit-target"});
  g.appendChild(hit);
  g.appendChild(nodeShape(n,r));

  let inner=null;
  if(n.cat!=="stat"){
    inner=nodeShape(n,Math.max(7,r-4));
    inner.setAttribute("class","inner-frame");
  }

  const src=iconFor(n);
  if(src&&n.cat!=="stat"){
    const id="clip_"+n.s.replace(/[^a-z0-9]/gi,"_");
    defs.appendChild(clipShape(n,r,id));
    const artRadius=(r-3)*ICON_ART_SCALE;
    const im=createSvg("image",{
      href:src,
      x:n.x-artRadius,
      y:n.y-artRadius,
      width:artRadius*2,
      height:artRadius*2,
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
  if(inner)g.appendChild(inner);

  g.setAttribute("role","button");
  g.setAttribute("tabindex","0");
  g.setAttribute("aria-label",displayTalentCn(n)+" / "+displayTalentEn(n));

  let pressX=0,pressY=0,dragged=false;
  g.addEventListener("pointerdown",e=>{
    pressX=e.clientX;pressY=e.clientY;dragged=false;
    g.classList.add("pressed");
  },{passive:true});
  g.addEventListener("pointermove",e=>{
    if(Math.hypot(e.clientX-pressX,e.clientY-pressY)>8){
      dragged=true;
      g.classList.remove("pressed");
    }
  },{passive:true});
  for(const evt of ["pointerup","pointercancel","pointerleave"]){
    g.addEventListener(evt,()=>g.classList.remove("pressed"),{passive:true});
  }
  g.addEventListener("mouseenter",()=>{
    if(!isDesktopInteraction())return;
    hotSlug=n.s;
    redraw();
    showInfo(n,false);
  });
  g.addEventListener("mouseleave",()=>{
    if(!isDesktopInteraction())return;
    hideInfo();
  });
  g.addEventListener("click",e=>{
    e.stopPropagation();
    if(dragged){
      dragged=false;
      return;
    }
    if(isDesktopInteraction()){
      hotSlug=n.s;
      if(n.s!==ROOT)toggleNode(n);
      redraw();
      showInfo(n,false);
      return;
    }
    const pop=$("#nodePopover");
    if(hotSlug===n.s&&pop&&!pop.classList.contains("hidden")){
      hideInfo();
      return;
    }
    hotSlug=n.s;
    redraw();
    showInfo(n,true);
  });
  g.addEventListener("contextmenu",e=>{
    if(!isDesktopInteraction())return;
    e.preventDefault();
    e.stopPropagation();
    hotSlug=n.s;
    if(n.s!==ROOT&&active.has(n.s))toggleNode(n);
    redraw();
    showInfo(n,false);
  });
  g.addEventListener("focus",()=>{
    if(!isDesktopInteraction())return;
    hotSlug=n.s;
    redraw();
    showInfo(n,false);
  });
  g.addEventListener("blur",()=>{
    if(!isDesktopInteraction())return;
    hideInfo();
  });
  g.addEventListener("keydown",e=>{
    if(!isDesktopInteraction()||n.s===ROOT)return;
    if(e.key==="Enter"||e.key===" "){
      e.preventDefault();
      hotSlug=n.s;
      toggleNode(n);
      redraw();
      showInfo(n,false);
    }else if((e.key==="Delete"||e.key==="Backspace")&&active.has(n.s)){
      e.preventDefault();
      hotSlug=n.s;
      toggleNode(n);
      redraw();
      showInfo(n,false);
    }
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

  hideInfo(false);
}
function pushUndo(){
  actionHistory.push([...active].filter(s=>s!==ROOT));
  if(actionHistory.length>40)actionHistory.shift();
  updateUndoButton();
}
function clearHistory(){
  actionHistory=[];
  updateUndoButton();
}
function updateUndoButton(){
  const b=$("#undoBtn");
  if(b)b.disabled=actionHistory.length===0;
}
function undoLast(){
  if(!actionHistory.length)return;
  const prev=actionHistory.pop();
  state.selected[selectionKey(CUR.key)]=prev;
  restoreSelection();
  persist();
  redraw();
  hideInfo(false);
  updateUndoButton();
  notify("已撤销上一步 / Undone");
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
      notify("不能移除：后续天赋仍依赖这个节点 / Downstream talents still depend on it");
      return;
    }
    pushUndo();
    active.delete(n.s);
  }else{
    if(!isAvail(n.s)){
      notify("该节点尚未连接到已选择路径 / This node is not connected yet");
      return;
    }
    if(points()>=CUR.budget){
      notify("30 点已用完 / All 30 talent points are spent");
      return;
    }
    const conflict=currentGroupConflict(n);
    if(conflict){
      notify(`同一组只能选一个：${conflict.cn||conflict.en} / Only one choice in this group`);
      return;
    }
    pushUndo();
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
    g.setAttribute("aria-pressed",active.has(n.s)?"true":"false");
    g.setAttribute("aria-disabled",n.s!==ROOT&&!active.has(n.s)&&!isAvail(n.s)?"true":"false");
    if(n.s===hotSlug) g.classList.add("hot");
  }

  for(const e of edgeEls){
    e.el.classList.toggle("on",active.has(e.a)&&active.has(e.b));
  }

  $("#pts").textContent=`${points()} / ${CUR.budget}`;
  setStatus(`${CUR.cn} · ${CUR.name} — ${patchLabel()} — ${CUR.nodes.length} nodes`,"ok");
}
function showInfo(n,focus=false){
  if(!n)return;
  const pop=$("#nodePopover");
  if(pop){
    pop.classList.remove("hidden");
    pop.setAttribute("aria-hidden","false");
  }
  const cat=CAT[n.cat]||CAT.passive;
  $("#infoType").textContent=`${cat.cn} / ${cat.en}`;
  $("#infoCn").textContent=displayTalentCn(n);
  $("#infoEn").textContent=displayTalentEn(n);

  let stateText="已选择 / Selected";
  if(n.s===ROOT)stateText="职业起点 / Root";
  else if(!active.has(n.s))stateText=isAvail(n.s)?"可选择 / Available":"未连接 / Locked";
  $("#infoState").textContent=stateText;

  const pair=descriptionPair(n);
  $("#infoCnDesc").textContent=pair.cn;
  $("#infoDesc").textContent=pair.en;
  const cnLabel=$("#infoCnLabel"),enLabel=$("#infoEnLabel"),source=$("#infoSource");
  if(pair.source==="paired-enhanced"){
    if(cnLabel)cnLabel.textContent="中文详细机制 / Chinese enhanced";
    if(enLabel)enLabel.textContent="英文详细机制 / English enhanced";
    if(source)source.textContent="优先使用成对维护的中英机制说明；两种语言来自同一说明层。 / Preferred paired maintained bilingual mechanics from the same source layer.";
  }else if(pair.source==="fatshark-preview-zh"){
    if(cnLabel)cnLabel.textContent="中文说明（更新预览） / Chinese preview";
    if(enLabel)enLabel.textContent="英文原文 / English";
    if(source)source.textContent="简中依据更新预览译文，并与当前英文数值核对。 / Preview translation checked against current numeric values.";
  }else if(pair.source==="manual-reviewed"||pair.source==="manual-reviewed-current-tooltip"){
    if(cnLabel)cnLabel.textContent="中文说明（人工复核） / Chinese reviewed";
    if(enLabel)enLabel.textContent="英文原文 / English";
    if(source)source.textContent=pair.source==="manual-reviewed-current-tooltip"
      ?"现有维护译文与当前机制不一致或缺失；本条按当前英文逐条复核，并由数字审计校验。 / Existing maintained text is missing or stale; this line is reviewed against the current tooltip and numerically audited."
      :"逐条对照英文原文人工复核；数值由自动审计再次校验。 / Manually reviewed against the English source; mechanics numbers are re-checked automatically.";
  }else if(pair.source==="stat-source-missing"){
    if(cnLabel)cnLabel.textContent="属性说明 / Stat";
    if(enLabel)enLabel.textContent="数据说明 / Data note";
    if(source)source.textContent="当前预览数据源只提供了属性节点名称，没有可靠的具体数值，因此不猜测数值。 / The preview source exposes the stat-node name but not a reliable exact value, so no value is guessed.";
  }else{
    if(cnLabel)cnLabel.textContent="中文说明 / Chinese";
    if(enLabel)enLabel.textContent="英文原文 / English";
    if(source)source.textContent=pair.source==="english-only"
      ?"当前没有可靠的一一对应简中来源，因此不再显示自动拼接翻译。 / No reliable one-to-one Chinese source; automatic word-substitution translation is suppressed."
      :"";
  }
  const mechanics=$("#infoMechanics");
  if(mechanics){
    if(n.mechanicsCn||n.mechanicsEn){
      mechanics.hidden=false;
      $("#infoMechanicsCn").textContent=n.mechanicsCn||"";
      $("#infoMechanicsEn").textContent=n.mechanicsEn||"";
    }else{
      mechanics.hidden=true;
      $("#infoMechanicsCn").textContent="";
      $("#infoMechanicsEn").textContent="";
    }
  }
  const provenance=$("#infoProvenance");
  if(provenance){
    const labels={
      "games-lantern":"Games Lantern",
      "fatshark-official-preview":"Fatshark 官方更新预览 / official preview",
      "fatshark-official-bound-by-duty":"Fatshark 官方 Bound by Duty",
      "syuantsai-glossary":"Darktide 中文术语表 / maintained Chinese glossary",
      "enhanced-translation-table":"Enhanced Descriptions 翻译表",
      "syuantsai-fatshark-preview-translation":"Fatshark 更新预览的维护中文整理 / maintained Chinese preview transcription",
      "community-aligned":"Enhanced Descriptions 维护简中 / maintained zh-CN",
      "manual-reviewed":"无现成维护译文，逐条人工对照英文 / manually reviewed fallback",
      "manual-reviewed-current-tooltip":"维护译文与当前机制不一致时，按当前英文逐条复核 / exact current-tooltip review",
      "fatshark-preview-zh":"Fatshark 更新预览 + 维护中文整理",
      "stat-source-missing":"数据源未提供具体数值 / exact value unavailable",
      "manual-name-fallback":"缺少现成译名 / no maintained title",
      "source-name-untranslated":"保留原名 / source name retained",
      "darktide-game-source+fatshark-official":"Darktide 游戏实现 + Fatshark 官方说明",
      "fatshark-official-preview+syuantsai-preview-translation":"Fatshark 官方更新预览 + 维护中文整理"
    };
    const bits=[];
    if(n.descSourceEn)bits.push("EN: "+(labels[n.descSourceEn]||n.descSourceEn));
    if(n.nameSourceCn)bits.push("中文名: "+(labels[n.nameSourceCn]||n.nameSourceCn));
    if(n.descSource)bits.push("中文说明: "+(labels[n.descSource]||n.descSource));
    if(n.mechanicsSource)bits.push("机制: "+(labels[n.mechanicsSource]||n.mechanicsSource));
    provenance.textContent=bits.length?"来源 / Sources · "+bits.join(" · "):"";
  }

  const vocab=$("#infoVocab");
  if(vocab){
    const text=pair.en||n.desc||"";
    const matches=[];
    const seen=new Set();
    for(const [en,cn] of VOCAB){
      if(text.toLowerCase().includes(en.toLowerCase())&&!seen.has(en.toLowerCase())){
        matches.push('<span class="v"><b>'+en+'</b> · '+cn+'</span>');
        seen.add(en.toLowerCase());
      }
      if(matches.length>=6)break;
    }
    vocab.innerHTML=matches.join("");
  }
  updateInfoAction(n);
  placePopover(n,focus);
}
function setTreeTop(){
  treeTop=BASE_TREE_TOP;
  const canvas=$("#treeCanvas"),svg=$("#treeSvg");
  if(!canvas||!svg||!CUR)return;
  const vw=CUR.viewbox[2],vh=CUR.viewbox[3];
  const height=svg.clientWidth*vh/vw;
  canvas.style.height=(BASE_TREE_TOP+height+28)+"px";
  canvas.style.setProperty("--tree-top",BASE_TREE_TOP+"px");
  svg.style.top=BASE_TREE_TOP+"px";
}
function updateInfoAction(n){
  const b=$("#infoAction");
  if(!b)return;
  b.hidden=n.s===ROOT;
  b.disabled=false;
  if(n.s===ROOT)return;
  if(active.has(n.s)){
    b.textContent="移除天赋 / Remove";
    b.dataset.mode="remove";
  }else if(isAvail(n.s)){
    b.textContent="选择天赋 / Select";
    b.dataset.mode="select";
  }else{
    b.textContent="需要前置节点 / Requires path";
    b.dataset.mode="locked";
    b.disabled=true;
  }
}
function placePopover(n,focus=false){
  const pop=$("#nodePopover"),nodeEl=nodeEls[n.s];
  if(!pop||!nodeEl||!CUR)return;

  requestAnimationFrame(()=>{
    const nr=nodeEl.getBoundingClientRect();
    const header=document.querySelector(".site-head");
    const hb=header?header.getBoundingClientRect().bottom:0;
    const vv=window.visualViewport;
    const layoutW=document.documentElement.clientWidth||window.innerWidth;
    const visualW=vv?vv.width:layoutW;
    const vw=Math.min(layoutW,visualW,window.innerWidth||layoutW);
    const vh=vv?vv.height:window.innerHeight;
    const vLeft=(vv&&visualW<layoutW)?vv.offsetLeft:0;
    const vTop=vv?vv.offsetTop:0;
    const vRight=vLeft+vw;
    const vBottom=vTop+vh;
    const margin=10;
    const gap=12;
    const minTop=Math.max(vTop+margin,hb+margin);

    const desktop=isDesktopInteraction();
    // Touch: center a compact card in the visual viewport.
    // Desktop: use a wider hover card while keeping it clear of screen edges.
    const cardMax=desktop?430:330;
    const cardMin=desktop?330:240;
    const cardHeightMax=desktop?620:430;
    pop.style.maxWidth=Math.max(cardMin,vw-2*margin)+"px";
    pop.style.width=Math.min(cardMax,Math.max(cardMin,vw-2*margin))+"px";

    const natural=Math.min(pop.scrollHeight||cardHeightMax,cardHeightMax);
    const above=Math.max(0,nr.top-minTop-gap);
    const below=Math.max(0,vBottom-nr.bottom-gap-margin);

    let side;
    if(above>=Math.min(natural,220)) side="above";
    else if(below>=Math.min(natural,220)) side="below";
    else side=above>=below?"above":"below";

    const available=Math.max(100,side==="above"?above:below);
    pop.style.maxHeight=Math.min(cardHeightMax,available)+"px";

    const pr=pop.getBoundingClientRect();
    const pw=pr.width;
    const ph=pr.height;
    const nodeX=nr.left+nr.width/2;
    const left=!desktop||vw<=620
      ?vLeft+(vw-pw)/2
      :Math.max(vLeft+margin,Math.min(vRight-pw-margin,nodeX-pw/2));
    const top=side==="above"
      ?Math.max(minTop,nr.top-gap-ph)
      :Math.min(vBottom-margin-ph,nr.bottom+gap);
    const arrow=Math.max(18,Math.min(pw-18,nodeX-left));

    pop.dataset.side=side;
    pop.style.left=left+"px";
    pop.style.top=top+"px";
    pop.style.setProperty("--arrow-left",arrow+"px");

    // No automatic page/tree movement. The surface adapts to the node, not vice versa.
    if(focus){
      const vr=$("#treeViewport")?.getBoundingClientRect();
      if(vr&&(nr.right<vr.left||nr.left>vr.right||nr.bottom<vr.top||nr.top>vr.bottom)){
        hideInfo();
      }
    }
  });
}
function hideInfo(redrawTree=true){
  const pop=$("#nodePopover");
  if(pop){
    pop.classList.add("hidden");
    pop.setAttribute("aria-hidden","true");
  }
  if(hotSlug!==null){
    hotSlug=null;
    if(redrawTree&&CUR)redraw();
  }
}
function notify(message){
  const toast=$("#toast");
  if(!toast)return;
  toast.textContent=message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>toast.classList.remove("show"),1700);
}
function setStatus(msg,type=""){
  const el=$("#status");
  el.textContent=msg;
  el.className="status"+(type?" "+type:"");
}
function applyZoom(){
  if(!CUR)return;
  const vp=$("#treeViewport"),canvas=$("#treeCanvas"),svg=$("#treeSvg");
  const vw=CUR.viewbox[2],vh=CUR.viewbox[3];
  const base=isDesktopInteraction()
    ?Math.max(760,Math.min(1120,vp.clientWidth*.92))
    :Math.max(455,Math.min(700,vp.clientWidth*1.13));
  const width=base*state.zoom,height=width*vh/vw;
  canvas.style.width=width+"px";
  svg.style.width=width+"px";
  svg.style.height=height+"px";
  setTreeTop();
  const n=hotSlug?nodeMap[hotSlug]:null;
  if(n&&!$("#nodePopover").classList.contains("hidden"))placePopover(n,false);
}
function centerTree(){
  const vp=$("#treeViewport"),canvas=$("#treeCanvas");
  vp.scrollLeft=Math.max(0,(canvas.clientWidth-vp.clientWidth)/2);
}
function renderAll(center=false){
  treeTop=BASE_TREE_TOP;
  renderBuildLibrary();
  renderPatchControls();
  renderClassbar();
  renderSubtreeBar();
  $("#buildName").value=state.name||"";
  $("#notes").value=state.notes||"";
  renderGearSuggestions();
  applyLoadout();
  hotSlug=null;
  buildTree();
  if(center)requestAnimationFrame(centerTree);
}
function buildPayload(){
  saveSelection();
  persist();
  return {
    format:"DTB3",
    patch:state.patch,
    classKey:state.classKey,
    selected:state.selected,
    name:state.name,
    notes:state.notes,
    loadouts:state.loadouts
  };
}
function base64urlEncode(text){
  const bytes=new TextEncoder().encode(text);
  let bin="";
  for(const b of bytes)bin+=String.fromCharCode(b);
  return btoa(bin).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
}
function base64urlDecode(text){
  let s=text.replace(/-/g,"+").replace(/_/g,"/");
  while(s.length%4)s+="=";
  const bin=atob(s);
  const bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}
function exportData(){
  return "DTB3."+base64urlEncode(JSON.stringify(buildPayload()));
}
function shareURL(){
  const u=new URL(location.href);
  u.search="";
  u.hash="b="+exportData();
  return u.toString();
}
function importData(txt){
  txt=(txt||"").trim();
  let x;
  if(txt.startsWith("DTB3.")){
    x=JSON.parse(base64urlDecode(txt.slice(5)));
  }else if(txt.startsWith("{")){
    x=JSON.parse(txt);
  }else if(txt.includes("#b=")){
    x=JSON.parse(base64urlDecode(txt.split("#b=DTB3.")[1]||""));
  }else{
    throw new Error("无法识别的 BD 数据 / Unsupported build format");
  }
  if(!["DTB3","Darktide-Future-Tree-BD-1","Darktide-Future-Tree-BD-2"].includes(x.format)){
    throw new Error("不是本规划器的 BD 数据 / Unsupported build format");
  }
  state.patch=(x.patch==="live"||x.patch==="future")?x.patch:"future";
  state.classKey=x.classKey||state.classKey;
  state.selected=x.selected||{};
  state.name=x.name||"";
  state.notes=x.notes||"";
  state.loadouts=x.loadouts||state.loadouts||{};
  syncActiveBuild();
  writeStorage();
  renderAll(true);
  persist();
  renderBuildLibrary();
}
function bind(){
  setupEquipmentPickers();
  $("#buildSelect").onchange=e=>switchSavedBuild(e.target.value);
  $("#newBuildBtn").onclick=()=>createSavedBuild(false);
  $("#duplicateBuildBtn").onclick=()=>createSavedBuild(true);
  $("#deleteBuildBtn").onclick=deleteSavedBuild;
  $("#undoBtn").onclick=undoLast;
  $("#resetBtn").onclick=()=>{
    if(points()===0){
      notify("当前天赋树已经是空的 / This tree is already empty");
      return;
    }
    if(confirm("重置当前职业的天赋？ / Reset this class tree?")){
      pushUndo();
      state.selected[selectionKey(state.classKey)]=[];
      hotSlug=null;
      persist();
      renderAll(false);
      notify("已重置当前天赋树 / Current tree reset");
    }
  };
  $("#infoAction").onclick=()=>{
    if(isDesktopInteraction())return;
    const n=hotSlug?nodeMap[hotSlug]:null;
    if(!n||n.s===ROOT)return;
    const wasActive=active.has(n.s);
    toggleNode(n);
    redraw();
    showInfo(n,false);
    if(wasActive&&active.has(n.s)){
      notify("该天赋仍被后续节点依赖 / Downstream nodes still depend on it");
    }else if(wasActive){
      notify("已移除天赋 / Talent removed");
    }else if(active.has(n.s)){
      notify("已选择天赋 / Talent selected");
    }
  };
  $("#futurePatchBtn").onclick=()=>switchPatch("future");
  $("#livePatchBtn").onclick=()=>switchPatch("live");
  $("#saveBtn").onclick=()=>{
    saveSelection();
    persist();
    renderBuildLibrary();
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
    requestAnimationFrame(centerTree);
  };
  $("#buildName").oninput=()=>{
    state.name=$("#buildName").value;
    persist();
    renderBuildLibrary();
  };
  $("#notes").oninput=()=>{state.notes=$("#notes").value;persist();};
  for(const id of LOADOUT_FIELDS){
    const el=document.getElementById(id);
    if(el)el.addEventListener("input",persist);
  }

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
      $("#dialogMsg").textContent="代码已复制 / Code copied ✓";
    }catch(_){
      $("#codeBox").select();
      document.execCommand("copy");
      $("#dialogMsg").textContent="代码已复制 / Code copied ✓";
    }
  };
  $("#copyLinkBtn").onclick=async()=>{
    const text=shareURL();
    try{
      await navigator.clipboard.writeText(text);
      $("#dialogMsg").textContent="分享链接已复制 / Share link copied ✓";
    }catch(_){
      $("#dialogMsg").textContent=text;
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

  syncInputMode();
  const syncPointerMode=()=>{
    const wasDesktop=document.documentElement.classList.contains("desktop-input");
    syncInputMode();
    const nowDesktop=isDesktopInteraction();
    if(wasDesktop!==nowDesktop){
      hideInfo();
      applyZoom();
      requestAnimationFrame(centerTree);
    }
  };
  if(POINTER_MEDIA.addEventListener)POINTER_MEDIA.addEventListener("change",syncPointerMode);

  document.addEventListener("keydown",e=>{
    if(!isDesktopInteraction())return;
    const tag=(e.target&&e.target.tagName||"").toLowerCase();
    const typing=tag==="input"||tag==="textarea"||e.target?.isContentEditable;
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="z"){
      e.preventDefault();
      undoLast();
      return;
    }
    if(typing)return;
    if(e.key==="0"||e.key.toLowerCase()==="f"){
      e.preventDefault();
      state.zoom=1;
      applyZoom();
      requestAnimationFrame(centerTree);
      persist();
    }else if(e.key==="+"||e.key==="="){
      e.preventDefault();
      state.zoom=Math.min(1.9,state.zoom*1.12);
      applyZoom();
      persist();
    }else if(e.key==="-"){
      e.preventDefault();
      state.zoom=Math.max(.72,state.zoom/1.12);
      applyZoom();
      persist();
    }
  });
  const desktopTree=$("#treeViewport");
  if(desktopTree){
    desktopTree.addEventListener("wheel",e=>{
      if(!isDesktopInteraction()||!e.ctrlKey)return;
      e.preventDefault();
      state.zoom=e.deltaY<0?Math.min(1.9,state.zoom*1.08):Math.max(.72,state.zoom/1.08);
      applyZoom();
      persist();
    },{passive:false});
  }

  const pop=$("#nodePopover");
  if(pop)pop.addEventListener("pointerdown",e=>e.stopPropagation());

  const treeVp=$("#treeViewport");
  if(treeVp){
    let treeGesture=false;
    treeVp.addEventListener("pointerdown",e=>{
      treeGesture=!(e.target instanceof Element&&e.target.closest(".node"));
    },{passive:true});
    treeVp.addEventListener("pointermove",()=>{
      if(treeGesture&&!$("#nodePopover").classList.contains("hidden"))hideInfo();
    },{passive:true});
    treeVp.addEventListener("pointerup",()=>{treeGesture=false;},{passive:true});
    treeVp.addEventListener("pointercancel",()=>{treeGesture=false;},{passive:true});
    treeVp.addEventListener("scroll",()=>{
      if(VISUAL_POPOVER_TEST)return;
      if(!$("#nodePopover").classList.contains("hidden"))hideInfo();
    },{passive:true});
  }
  document.addEventListener("pointerdown",e=>{
    const card=$("#nodePopover");
    if(!card||card.classList.contains("hidden"))return;
    const target=e.target;
    if(card.contains(target))return;
    if(target instanceof Element&&target.closest(".node"))return;
    hideInfo();
  },{passive:true});
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape")hideInfo();
  });
  let popoverScrollRaf=0;
  addEventListener("scroll",()=>{
    if(VISUAL_POPOVER_TEST)return;
    const card=$("#nodePopover");
    const n=hotSlug?nodeMap[hotSlug]:null;
    if(!card||card.classList.contains("hidden")||!n)return;
    cancelAnimationFrame(popoverScrollRaf);
    popoverScrollRaf=requestAnimationFrame(()=>{
      const nr=nodeEls[n.s]?.getBoundingClientRect();
      const hb=document.querySelector(".site-head")?.getBoundingClientRect().bottom||0;
      if(!nr||nr.bottom<hb||nr.top>innerHeight){
        hideInfo();
      }else{
        placePopover(n,false);
      }
    });
  },{passive:true});

  addEventListener("resize",()=>{
    hideInfo();
    applyZoom();
    requestAnimationFrame(centerTree);
  });
  addEventListener("hashchange",()=>{
    const raw=location.hash.startsWith("#b=")?location.hash.slice(3):"";
    if(raw){
      try{importData(raw);}catch(_){}
    }
  });
  addEventListener("pagehide",()=>{
    try{
      saveSelection();
      persist();
    }catch(_){}
  });
}
function selfCheck(){
  if(!DATA||!Array.isArray(DATA.classes)||DATA.classes.filter(c=>!c.parent).length<7) throw new Error("all seven class trees are not loaded");
  if(!DATA.classes.find(c=>c.key==="hivescum-stimm")) throw new Error("Hive Scum Stimm Lab is not loaded");
  if(!Array.isArray(DATA.liveClasses)||DATA.liveClasses.filter(c=>!c.parent).length<7) throw new Error("live patch trees are not loaded");
  if(!DATA) throw new Error("talent data is missing");
  if(!CUR||CUR.nodes.length<40) throw new Error("talent tree data is incomplete");
  if(!ROOT||!nodeMap[ROOT]) throw new Error("class root is missing");
  if(Object.keys(nodeEls).length!==CUR.nodes.length) throw new Error("not all nodes rendered");
  if(!$("#nodePopover")) throw new Error("node popover is missing");
  if(treeTop!==BASE_TREE_TOP) throw new Error("tree top shifted unexpectedly");
  if(!$("#buildSelect")||!Array.isArray(state.builds)||!state.builds.length) throw new Error("build library is missing");
  if(!$("#meleeWeapon")||!$("#rangedWeapon")||!$("#curio1Type")||!$("#curio1Main")) throw new Error("loadout editor is missing");
  if(!document.querySelector("#meleeWeapon + .picker-toggle")&&!$("#meleeWeapon").closest(".picker-host")) throw new Error("weapon picker is missing");
  for(const tree of [...DATA.classes,...DATA.liveClasses]){
    for(const n of tree.nodes){
      if(/[A-F0-9]{8,}$/i.test(displayTalentEn(n)))throw new Error("internal talent id leaked into display name");
      const zh=getChineseDescription(n);
      if(/\{#(?:color|reset)/i.test(zh))throw new Error("game markup leaked into Chinese description");
    }
  }
}

function runDesktopSelfTest(){
  if(!DESKTOP_TEST)return;
  try{
    syncInputMode();
    if(!isDesktopInteraction())throw new Error("desktop interaction mode not active");
    const before=points();
    const firstAvail=CUR.nodes.find(n=>isAvail(n.s));
    if(!firstAvail)throw new Error("no selectable desktop node");
    const el=nodeEls[firstAvail.s];

    el.dispatchEvent(new MouseEvent("mouseenter",{bubbles:false}));
    if(points()!==before)throw new Error("desktop hover changed talent points");
    if($("#nodePopover").classList.contains("hidden"))throw new Error("desktop hover did not show details");

    el.dispatchEvent(new MouseEvent("mouseleave",{bubbles:false}));
    if(!$("#nodePopover").classList.contains("hidden"))throw new Error("desktop mouseleave did not hide details");

    el.dispatchEvent(new MouseEvent("mouseenter",{bubbles:false}));
    el.dispatchEvent(new MouseEvent("click",{bubbles:true}));
    if(points()!==before+1)throw new Error("desktop left click did not select talent");

    el.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,button:2}));
    if(points()!==before)throw new Error("desktop right click did not remove talent");

    el.dispatchEvent(new MouseEvent("click",{bubbles:true}));
    if(points()!==before+1)throw new Error("desktop second select failed");
    el.dispatchEvent(new MouseEvent("click",{bubbles:true}));
    if(points()!==before)throw new Error("desktop second left click did not remove talent");

    document.body.dataset.desktoptest="pass";
  }catch(e){
    document.body.dataset.desktoptest="fail";
    document.body.dataset.desktoptestError=String(e.message||e);
  }
}

function runVisualPopoverTest(){
  if(!VISUAL_POPOVER_TEST)return;
  try{
    const candidate=CUR.nodes
      .filter(n=>n.cat!=="root"&&n.desc)
      .sort((a,b)=>a.y-b.y)[0]
      ||CUR.nodes.find(n=>n.cat!=="root");
    if(!candidate)throw new Error("no visual-test candidate");
    const node=nodeEls[candidate.s];
    const before=node.getBoundingClientRect().top;
    hotSlug=candidate.s;
    redraw();
    showInfo(candidate,false);
    document.body.dataset.visualTestStarted="true";

    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      try{
        const pop=$("#nodePopover");
        if(!pop||!node)throw new Error("popover or node missing");
        const pr=pop.getBoundingClientRect();
        const nr=node.getBoundingClientRect();
        const headerBottom=document.querySelector(".site-head").getBoundingClientRect().bottom;
        const arrow=parseFloat(pop.style.getPropertyValue("--arrow-left")||"0");
        const arrowX=pr.left+arrow;
        const nodeX=nr.left+nr.width/2;
        const side=pop.dataset.side||"";
        const vv=window.visualViewport;
        const layoutW=document.documentElement.clientWidth||innerWidth;
        const visualW=vv?vv.width:layoutW;
        const safeW=Math.min(layoutW,visualW,innerWidth||layoutW);
        const vl=(vv&&visualW<layoutW)?vv.offsetLeft:0,vt=vv?vv.offsetTop:0;
        const vr=vl+safeW,vb=vt+(vv?vv.height:innerHeight);
        const relation=side==="above"?pr.bottom<=nr.top+16:pr.top>=nr.bottom-16;
        const insideX=pr.left>=vl+8&&pr.right<=vr-8;
        const insideY=pr.top>=Math.max(vt+6,headerBottom+6)&&pr.bottom<=vb-6;
        document.body.dataset.popoverXError=String(Math.round(Math.abs(arrowX-nodeX)));
        document.body.dataset.popoverInsideX=String(insideX);
        document.body.dataset.popoverInsideY=String(insideY);
        document.body.dataset.popoverRelation=String(relation);
        document.body.dataset.popoverSide=side;
        document.body.dataset.treeShift=String(Math.round(Math.abs(nr.top-before)));
        document.body.dataset.visualWidth=String(Math.round(vr-vl));
        document.body.dataset.visualHeight=String(Math.round(vb-vt));
        document.body.dataset.popoverLeft=String(Math.round(pr.left));
        document.body.dataset.popoverRight=String(Math.round(pr.right));
        document.body.dataset.popoverTop=String(Math.round(pr.top));
        document.body.dataset.popoverBottom=String(Math.round(pr.bottom));
        document.body.dataset.headerBottom=String(Math.round(headerBottom));
        document.body.dataset.visualTestDone="true";
      }catch(e){
        document.body.dataset.popoverVisualError=String(e.message||e);
      }
    }));
  }catch(e){
    document.body.dataset.popoverVisualError=String(e.message||e);
  }
}

function runAutomatedSelfTest(){
  if(new URLSearchParams(location.search).get("selftest")!=="1")return;
  try{
    const before=points();
    const firstAvail=CUR.nodes.find(n=>isAvail(n.s));
    if(!firstAvail)throw new Error("no selectable first node");

    nodeEls[firstAvail.s].dispatchEvent(new MouseEvent("click",{bubbles:true}));
    if(points()!==before)throw new Error("preview tap changed talent points");
    if($("#nodePopover").classList.contains("hidden"))throw new Error("talent preview did not open");

    nodeEls[firstAvail.s].dispatchEvent(new MouseEvent("click",{bubbles:true}));
    if(!$("#nodePopover").classList.contains("hidden"))throw new Error("same-node tap did not dismiss");

    nodeEls[firstAvail.s].dispatchEvent(new MouseEvent("click",{bubbles:true}));
    $("#infoAction").click();
    if(points()!==before+1)throw new Error("explicit select did not spend a point");
    if($("#nodePopover").classList.contains("hidden"))throw new Error("card closed after explicit select");

    undoLast();
    if(points()!==before)throw new Error("undo did not restore points");
    hotSlug=firstAvail.s;
    toggleNode(firstAvail);
    redraw();

    const melee=$("#meleeWeapon");
    melee.value="SELFTEST WEAPON";
    melee.dispatchEvent(new Event("input",{bubbles:true}));
    if(currentLoadout().meleeWeapon!=="SELFTEST WEAPON")throw new Error("loadout did not persist");

    const pickerHost=melee.closest(".picker-host");
    const pickerMenu=pickerHost?.querySelector(".picker-menu");
    const pickerToggle=pickerHost?.querySelector(".picker-toggle");
    if(!pickerHost||!pickerMenu||!pickerToggle)throw new Error("weapon searchable picker missing");
    melee.value="";
    melee.dispatchEvent(new Event("input",{bubbles:true}));
    pickerMenu.hidden=true;
    pickerToggle.click();
    const firstWeapon=pickerMenu.querySelector(".picker-option");
    if(pickerMenu.hidden||!firstWeapon)throw new Error("weapon picker did not open with choices");
    firstWeapon.click();
    if(!melee.value||currentLoadout().meleeWeapon!==melee.value)throw new Error("weapon picker selection did not persist");

    const code=exportData();
    if(!code.startsWith("DTB3."))throw new Error("compact build code not generated");

    saveSelection();
    state.patch="live";
    state.classKey="veteran";
    renderAll(false);
    if(CUR.patch!=="live"||CUR.nodes.length<40)throw new Error("live patch did not render");

    saveSelection();
    state.patch="future";
    state.classKey="psyker";
    renderAll(false);
    const battle=CUR.nodes.find(n=>displayTalentEn(n)==="Battle Meditation");
    if(battle){
      const battlePair=descriptionPair(battle);
      if(!/降低\s*10%|10%[^。；]*降低/.test(battlePair.cn||""))throw new Error("Battle Meditation reduction meaning missing");
      if(!/平息\s*10%/.test(battlePair.cn||""))throw new Error("Battle Meditation Quell terminology mismatch");
      if(!/10%/.test(battlePair.en||""))throw new Error("Battle Meditation English pair missing");
    }
    const smite=CUR.nodes.find(n=>displayTalentEn(n)==="Smite");
    if(smite){
      const smitePair=descriptionPair(smite);
      if(/\{#|\{[A-Za-z0-9_]+(?::%s)?\}/.test(smitePair.cn||""))throw new Error("Smite raw markup leaked into displayed Chinese");
      if(smitePair.source==="paired-enhanced"&&(!/16/.test(smitePair.cn||"")||!/16/.test(smitePair.en||"")))throw new Error("Smite maintained pair lost range mechanics");
    }
    const dream=CUR.nodes.find(n=>displayTalentEn(n)==="Just a Dream");
    if(!dream)throw new Error("Just a Dream node missing");
    const dreamPair=descriptionPair(dream);
    if(!/25%/.test(dreamPair.en||"")||!/25%/.test(dreamPair.cn||""))throw new Error("Just a Dream 25% conversion missing");
    if(!/97%/.test(dreamPair.en||"")||!/97%/.test(dreamPair.cn||""))throw new Error("Just a Dream 97% threshold missing");
    if(/提高.*最大(?:生命|韧性)|最大(?:生命|韧性).*提高/.test(dreamPair.cn||""))throw new Error("Just a Dream incorrectly claims a max-stat increase");
    const statNode=CUR.nodes.find(n=>n.cat==="stat");
    if(statNode&&/[A-F0-9]{8,}$/i.test(displayTalentEn(statNode)))throw new Error("stat node internal id leaked");

    const warp=CUR.nodes.find(n=>displayTalentEn(n)==="Warp Expenditure");
    if(!warp)throw new Error("Warp Expenditure node missing");
    const warpPair=descriptionPair(warp);
    if(!/[\u4e00-\u9fff]/.test(warpPair.cn||""))throw new Error("Warp Expenditure Chinese description missing");
    if(warpPair.source==="paired-enhanced"&&!warpPair.en)throw new Error("paired enhanced English description missing");
    showInfo(warp,false);
    if(!/[\u4e00-\u9fff]/.test($("#infoCnDesc").textContent||""))throw new Error("Chinese description not rendered");
    if(/\n/.test($("#infoCnDesc").textContent||""))throw new Error("Chinese description still contains source line breaks");

    saveSelection();
    state.classKey="hivescum-stimm";
    renderAll(false);
    if(!CUR||CUR.key!=="hivescum-stimm"||CUR.nodes.length<20)throw new Error("Stimm Lab did not render");

    document.body.dataset.selftest="pass";
    document.body.dataset.selftestNodes=String(CUR.nodes.length);
  }catch(e){
    document.body.dataset.selftest="fail";
    document.body.dataset.selftestError=String(e.message||e);
  }
}

try{
  load();
  bind();
  const hashBuild=location.hash.startsWith("#b=")?location.hash.slice(3):"";
  if(hashBuild){
    try{importData(hashBuild);}catch(_){renderAll(false);}
  }else{
    renderAll(false);
  }
  selfCheck();
  runAutomatedSelfTest();
  runDesktopSelfTest();
  runVisualPopoverTest();
  // Render from the light core payload immediately; fetch only the selected class's art (~1 MB).
  queueCurrentIconPack();
  if("serviceWorker" in navigator){
    window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js?v=gl34").catch(()=>{}));
  }
}catch(e){
  setStatus("天赋树启动失败 / Talent tree failed to start: "+e.message,"err");
}
})();