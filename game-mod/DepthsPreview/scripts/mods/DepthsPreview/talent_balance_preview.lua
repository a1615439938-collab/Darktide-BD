local mod = get_mod("DepthsPreview")

local BuffSettings = require("scripts/settings/buff/buff_settings")
local BuffTemplates = require("scripts/settings/buff/buff_templates")
local PlayerAbilities = require("scripts/settings/ability/player_abilities/player_abilities")
local TalentSettings = require("scripts/settings/talent/talent_settings")

local stat_buffs = BuffSettings.stat_buffs

local Preview = {}
local changes = {}
local applied = false

local function set_value(target, key, value)
  if not target then
    return
  end
  changes[#changes + 1] = {
    target = target,
    key = key,
    value = target[key],
  }
  target[key] = value
end

local function set_stat(template, stat, value)
  if not template then
    return
  end
  if not template.stat_buffs then
    set_value(template, "stat_buffs", {})
  end
  set_value(template.stat_buffs, stat, value)
end

local function set_proc_stat(template, stat, value)
  if not template then
    return
  end
  if not template.proc_stat_buffs then
    set_value(template, "proc_stat_buffs", {})
  end
  set_value(template.proc_stat_buffs, stat, value)
end

local function patch_veteran()
  local t = TalentSettings.veteran_2

  -- Survivalist / Scavenger: 0.25% base, 0.5% improved, 5s cooldown.
  set_value(t.coherency, "ammo_replenishment_percent", 0.0025)
  set_value(t.coherency, "ammo_replenishment_percent_improved", 0.005)
  set_value(t.coherency, "cooldown", 5)

  -- Deadshot follow-up preview.
  set_value(t.offensive_2_2, "stamina_per_second", 0.33)

  -- Close and Kill: +7.5% movement speed aura.
  set_stat(BuffTemplates.veteran_movement_speed_coherency, stat_buffs.movement_speed, 0.075)

  -- Duty and Honour: +75 temporary max toughness.
  set_stat(BuffTemplates.veteran_combat_ability_increase_toughness_to_coherency, stat_buffs.toughness_bonus_flat, 75)

  -- Duck and Dive keeps the existing +30% stamina proc and gains +5% movement speed.
  set_stat(BuffTemplates.veteran_stamina_on_ranged_dodges, stat_buffs.movement_speed, 0.05)
end

local function patch_psyker()
  local base = TalentSettings.psyker
  local t = TalentSettings.psyker_2

  -- Perilous Combustion: 3 -> 2 Soulblaze stacks.
  set_value(t.offensive_1_3, "num_stacks", 2)

  -- Psykinetic's Aura: +50% cooldown regeneration for 3s.
  set_value(base.psyker_cooldown, "duration", 3)
  set_value(BuffTemplates.psyker_cooldown_buff, "duration", 3)

  -- The preview requires the Psyker's own kill, not an ally's kill.
  local aura = BuffTemplates.psyker_aura_cooldown_reduction_on_elite_kill
  if aura and aura.proc_func then
    set_value(aura, "proc_func", function (params, template_data, template_context, t_now)
      local tags = params.tags
      if not tags or not (tags.elite or tags.special) then
        return
      end
      if not template_context.is_server or params.attacking_unit ~= template_context.unit then
        return
      end
      template_context.buff_extension:add_internally_controlled_buff("psyker_cooldown_buff", t_now)
    end)
  end

  -- Mind in Motion: preserve no reload/quell movement penalty and add +5% movement.
  set_stat(BuffTemplates.psyker_venting_improvements, stat_buffs.movement_speed, 0.05)

  -- Surety of Arms: threshold 75% -> 80% Peril.
  set_value(base.reload_speed_warp, "threshold", 0.80)
end

local function patch_zealot()
  local base = TalentSettings.zealot
  local t = TalentSettings.zealot_2

  -- Until Death: 5s -> 8s, keeping the 120s cooldown.
  set_value(t.passive_2, "active_duration", 8)
  set_value(BuffTemplates.zealot_resist_death, "active_duration", 8)

  -- The live Holy Revenant variant also owns a resist-death window.
  if t.defensive_1 then
    set_value(t.defensive_1, "active_duration", 8)
  end
  if BuffTemplates.zealot_resist_death_improved_with_leech then
    set_value(BuffTemplates.zealot_resist_death_improved_with_leech, "active_duration", 8)
  end

  -- Faithful Frenzy gains +5% movement speed in addition to its current melee attack speed.
  set_stat(BuffTemplates.zealot_increased_melee_attack_speed, stat_buffs.movement_speed, 0.05)

  -- Retributor's Stance: 0.4% -> 0.5% toughness/sec per spent Momentum stack.
  set_value(base.zealot_momentum_toughness_replenish, "toughness_to_restore", 0.005)

  -- Unseen Blade: 15% -> 20% damage against enemies not targeting the Zealot.
  set_value(base.zealot_damage_vs_nonthreat, "damage_vs_nonthreat", 0.20)
  set_stat(BuffTemplates.zealot_damage_vs_nonthreat, stat_buffs.damage_vs_nonthreat, 0.20)
end

local function patch_ogryn()
  local shared = TalentSettings.ogryn_shared
  local gunlugger = TalentSettings.ogryn_1
  local bonebreaker = TalentSettings.ogryn_2

  -- Soften Them Up is already 15% / 5s in the current client data; keep that value explicit.
  set_value(shared.ogryn_staggering_increases_damage_taken, "damage", 0.15)
  set_value(shared.ogryn_staggering_increases_damage_taken, "duration", 5)

  -- Maximum Firepower: 100% cooldown regeneration for 2.5s on Lucky Bullet.
  set_value(gunlugger.spec_passive_1, "duration", 2.5)
  set_value(gunlugger.spec_passive_1, "increased_cooldown_regeneration", 1)
  if BuffTemplates.ogryn_no_ammo_consumption_passive_cooldown_buff then
    set_value(BuffTemplates.ogryn_no_ammo_consumption_passive_cooldown_buff, "duration", 2.5)
  end

  -- Bruiser: 50% cooldown regeneration for 4s after a coherency Elite kill.
  set_value(bonebreaker.coop_3, "duration", 4)
  set_value(bonebreaker.coop_3, "increased_cooldown_regeneration", 0.5)
  if BuffTemplates.ogryn_cooldown_on_elite_kills_by_coherence then
    set_value(BuffTemplates.ogryn_cooldown_on_elite_kills_by_coherence, "duration", 4)
  end

  -- Dominate: 10% -> 15% Rending for 10s on Elite kill.
  set_proc_stat(BuffTemplates.ogryn_rending_on_elite_kills, stat_buffs.rending_multiplier, 0.15)

  -- Indomitable base cooldown: 30s -> 25s.
  set_value(bonebreaker.combat_ability, "cooldown", 25)
  if PlayerAbilities.ogryn_charge then
    set_value(PlayerAbilities.ogryn_charge, "cooldown", 25)
  end

  -- Go Again!: 2% -> 1.5% cooldown on stagger.
  if BuffTemplates.ogryn_taunt_staggers_reduce_cooldown then
    set_value(BuffTemplates.ogryn_taunt_staggers_reduce_cooldown, "cooldown_reduction_percentage", 0.015)
  end

  -- Keep Shooting: 15% -> 20% reload speed on an empty magazine.
  set_value(shared.ogryn_reload_speed_on_empty, "reload_speed", 0.20)
  set_stat(BuffTemplates.ogryn_reload_speed_on_empty, stat_buffs.reload_speed, 0.20)
end

function Preview.apply()
  if applied then
    return
  end
  applied = true

  patch_veteran()
  patch_psyker()
  patch_zealot()
  patch_ogryn()
end

function Preview.restore()
  if not applied then
    return
  end

  for i = #changes, 1, -1 do
    local change = changes[i]
    change.target[change.key] = change.value
  end

  table.clear(changes)
  applied = false
end

return Preview
