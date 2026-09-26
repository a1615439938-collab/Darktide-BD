// Current weapon-family blessing compatibility supplements.
// Sources are current Games Lantern weapon pages for weapon families that are newer
// than the maintained local tier-note dataset. English names remain canonical.
window.WEAPON_BLESSING_OVERRIDES={
  "Huntsman's Shotgun":[
    "Born in blood","Deathspitter","Flechette","Full Bore","Gloryhunter",
    "No Respite","Scattershot","Speedload","Terrifying Barrage"
  ],
  "Paired Transonic Blades":[
    "Bladed Momentum","Deadly Frequencies","Perfect Strike","Precognition","Rampage",
    "Riposte","Savage Sweep","Shred","Superiority"
  ],
  "Arc Maul":[
    "All or Nothing","Confident Strike","Enhanced Voltaic Arcs","Execution","Hammerblow",
    "Lightning Reflexes","Overwhelming Force","Thunderous","Voltagheist Overload"
  ],
  "Galvanic Rifle":[
    "Between the Eyes","Deadly Accurate","Ghost","Gloryhunter","Headhunter","Hot-Shot",
    "Man-Stopper","Opening Salvo","Pinpointing target","Trickshooter"
  ],
  "Phosphor Blast Pistol":[
    "Crucian Roulette","Gloryhunter","Hand-Cannon","Infernus","Man-Stopper","Opening Salvo",
    "Pinpointing target","Powderburn","Showstopper","Surgical"
  ],
  "Arc Rifle":[
    "Blaze Away","Cavalcade","Charmed Reload","Dumdum","Enhanced Voltaic Arcs",
    "Inspiring Barrage","No Respite","Overwhelming Fire","Roaring Advance"
  ],
  "Cruncher":[
    "All or Nothing","Execution","Hammerblow","Limbsplitter","Shock & Awe",
    "Slow and Steady","Take a Swing","Unstoppable Force"
  ],
  "Thugshot":[
    "Blaze Away","Expansive","Inspiring Barrage","Pierce","Punishing Fire",
    "Run 'n' Gun","Surgical","Terrifying Barrage"
  ]
};

window.EXTRA_BLESSINGS={
  "Deadly Frequencies":{
    cn:"致命频率",
    en:"Deadly Frequencies",
    effectCn:"武器特殊攻击命中敌人后，接下来的近战攻击获得 +30% 近战强度。",
    effectEn:"After hitting an enemy with your Weapon Special attack, your next melee attacks have +30% increased Melee Strength.",
    weaponEffects:{}
  },
  "Enhanced Voltaic Arcs":{
    cn:"强化电流弧",
    en:"Enhanced Voltaic Arcs",
    effectCn:"强化武器产生的电流弧，使其跳得更远并命中更多目标；具体数值取决于武器。",
    effectEn:"Enhances the weapon's Arc lightning with greater jump angle, distance and additional jumps; exact values depend on the weapon.",
    weaponEffects:{
      "Arc Maul":{
        cn:"电流弧跳跃角度 +12、跳跃距离 +2，并可额外跳跃 2 次。",
        en:"Arc lightning gains +12 jump angle and +2 jump distance, and can jump 2 additional times."
      },
      "Arc Rifle":{
        cn:"电流弧跳跃角度 +10、跳跃距离 +1，并可额外跳跃 1 次。",
        en:"Arc lightning gains +10 jump angle and +1 jump distance, and can jump 1 additional time."
      }
    }
  },
  "Voltagheist Overload":{
    cn:"电灵过载",
    en:"Voltagheist Overload",
    effectCn:"电流弧命中人类型敌人时有 12.5% 几率立即击杀；立即击杀不会触发其他潜在触发效果。",
    effectEn:"12.5% chance to Instakill Human-sized enemies hit by Arc lightning. Other potential triggers are not activated on Instakill.",
    weaponEffects:{}
  }
};
