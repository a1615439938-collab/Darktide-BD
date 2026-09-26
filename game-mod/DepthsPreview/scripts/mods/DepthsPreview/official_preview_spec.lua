-- Fatshark Depths of the Damned pre-release specification snapshot.
-- This file is intentionally standalone and human-auditable.
-- Sources:
-- https://forums.fatsharkgames.com/t/preview-upcoming-balance-changes/125587
-- https://www.playdarktide.com/news/new-free-update-depths-of-the-damned-coming-september-29
return {
  snapshot_date = "2026-09-27",
  target_release = "2026-09-29",
  new_weapons = {
    {
      name = "Ogryn Cruncher",
      kind = "new_family",
      class = { "ogryn" },
      preview = "Two-handed hammer; wide heavy swings; chargeable single-target strikedown special.",
      exact_client_assets_available = false,
    },
    {
      name = "Huntsman's Shotgun",
      kind = "new_family",
      class = { "veteran", "zealot", "psyker", "skitarii", "hivescum" },
      preview = "Pump-action pellet shotgun; close-medium range; slower/heavier than Combat Shotgun; flashlight special.",
      exact_client_assets_available = false,
    },
    {
      name = "Ogryn Thugshot",
      kind = "new_family",
      class = { "ogryn" },
      preview = "Single-projectile slug shotgun; precise, heavy damage, mid-long range.",
      exact_client_assets_available = false,
    },
    {
      name = "Crusher Krourk Mk VII",
      kind = "new_mark",
      class = { "zealot", "adamant" },
      preview = "Crusher variant with unique moveset; empowered explosive next-attack special with cooldown.",
      exact_client_assets_available = false,
    },
    {
      name = "Double-Barrelled Shotgun Krourk Mk IV",
      kind = "new_mark",
      class = { "veteran", "zealot", "psyker", "skitarii", "hivescum", "adamant" },
      preview = "Tighter spread; hip fire uses both barrels; alternate fire uses one barrel with ADS.",
      exact_client_assets_available = false,
    },
    {
      name = "Gromm Mk I Battle Maul and Mk V Slab Shield",
      kind = "new_mark",
      class = { "ogryn" },
      preview = "New light moveset focused on Strikedown; heavies retain crowd control.",
      exact_client_assets_available = false,
    },
  },
  base_class = {
    veteran = {
      toughness = 120,
      stamina_regen_delay = 0.5,
      notes = {
        "Deadshot stamina drain per second: 0.75 -> 0.33",
        "Guardsman iconic: +25% Ranged Damage",
        "Sharpshooter iconic: Elite/Specialist kills restore 1% Ammo, 5s cooldown",
      },
    },
    zealot = {
      toughness = 125,
      notes = {
        "Blood Redemption becomes baseline; melee-kill Toughness bonus becomes +75%",
      },
    },
    psyker = {
      critical_chance = 0.10,
    },
    ogryn = {
      toughness = 125,
      notes = {
        "Towering Presence becomes baseline; Coherency Radius bonus becomes +50%",
      },
    },
  },
  golden_toughness = {
    spillover_immunity = false,
  },
  blessings = {
    counterattack = {
      trigger = "on_block",
      duration = 6,
      refresh_while_active = true,
    },
    energy_transfer = {
      trigger = "on_block",
      refresh_while_active = true,
    },
    lightning_reflexes = {
      melee_strength_trigger = "on_block",
      stun_trigger = "on_perfect_block",
    },
  },
  weapon_balance = {
    ogryn_slab_shield = {
      "Increase Light Relentless damage on 2nd/3rd targets",
      "Pushfollow aligned to Light Strikedown",
      "Heavy 2 windup gains Melee Block",
      "Faster Push -> Pushfollow chain",
      "Pushfollow can chain to shield plant",
      "Light 4 chains to Light 3 / Heavy 1",
      "Light 3 and Light 4 loop with +10% attack speed",
      "Hitbox/range tweaks",
    },
    thunder_hammer = {
      status = "official preview contains detailed damage/profile/mark changes; implement against native profile templates",
    },
    anti_cancel = {
      "Force Staves", "Shivs", "Bone Saw", "Relic Blade", "Shock Maul",
      "Arbites Shock Maul", "Arbites Shock Maul and Shield", "Force Sword",
      "Force Greatsword", "Duelling Sword", "Combat Axe", "Tactical Axe", "Eviscerator",
    },
  },
}
