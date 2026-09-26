local mod = get_mod("DepthsPreview")

local Ammo = require("scripts/utilities/ammo")
local AttackSettings = require("scripts/settings/damage/attack_settings")
local Buff = require("scripts/extension_systems/buff/buffs/buff")
local BuffExtensionBase = require("scripts/extension_systems/buff/buff_extension_base")
local BuffSettings = require("scripts/settings/buff/buff_settings")
local DamageCalculation = require("scripts/utilities/attack/damage_calculation")
local DamageProfileTemplates = require("scripts/settings/damage/damage_profile_templates")
local DamageSettings = require("scripts/settings/damage/damage_settings")
local FixedFrame = require("scripts/utilities/fixed_frame")
local ActionZealotChannel = require("scripts/extension_systems/weapon/actions/action_zealot_channel")
local Toughness = require("scripts/utilities/toughness/toughness")
local WarpCharge = require("scripts/utilities/warp_charge")

local State = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_state")

local attack_types = AttackSettings.attack_types
local keywords = BuffSettings.keywords
local proc_events = BuffSettings.proc_events
local stat_buffs = BuffSettings.stat_buffs
local warp_damage_types = DamageSettings.warp_damage_types

local Runtime = {}
local runtime_by_unit = setmetatable({}, { __mode = "k" })
local installed = false

local NODE = {
  zealot = {
    voice_of_terra = "dp_the_voice_of_terra_2",
    out_of_pocket = "dp_out_of_pocket_2",
    wait_in_line = "dp_wait_in_line",
    holy_tools = "dp_holy_tools",
    got_your_back = "dp_got_your_back",
    purifying_hatred = "dp_purifying_hatred",
    zealous_pilgrim = "dp_zealous_pilgrim",
    holy_cause = "dp_holy_cause",
    ecclesiarchs_call = "dp_ecclesiarchs_call",
    chorus = "dp_chorus_of_spiritual_fortitude",
    shroudfield = "dp_shroudfield",
    fury = "dp_fury_of_the_faithful",
  },
  psyker = {
    focused_warp = "dp_focused_warp",
    peril_equilibrium = "dp_peril_equilibrium",
    psykinetic_grip = "dp_psykinetic_grip",
  },
  ogryn = {
    found_some_more = "dp_found_some_more",
  },
}

local function local_player()
  return Managers.player and Managers.player:local_player(1) or nil
end

local function is_local_player(player)
  local local_p = local_player()
  return local_p ~= nil and player == local_p
end

local function local_player_unit()
  local player = local_player()
  return player and player.player_unit or nil
end

local function class_key(player)
  local profile = player and player:profile()
  local archetype = profile and profile.archetype
  return archetype and archetype.name or nil
end

local function node_selected(player, node_id)
  local class = class_key(player)
  return State.enabled() and class and State.has_node(class, node_id)
end

local function runtime(unit)
  local data = runtime_by_unit[unit]
  if not data then
    data = {}
    runtime_by_unit[unit] = data
  end
  return data
end

local function mark_modified(stats, key)
  local modified = stats and stats._modified_stats
  if modified then
    modified[key] = true
  end
end

local function add_stat(stats, key, amount)
  if not stats or not key then
    return
  end
  stats[key] = (stats[key] or 1) + amount
  mark_modified(stats, key)
end

local function multiply_stat(stats, key, multiplier)
  if not stats or not key then
    return
  end
  stats[key] = (stats[key] or 1) * multiplier
  mark_modified(stats, key)
end

local psykinetic_profiles = {}
local function add_psykinetic_profile(name)
  local profile = DamageProfileTemplates[name]
  if profile then
    psykinetic_profiles[profile] = true
  end
end

for _, name in ipairs({
  -- Brain Rupture / Brain Burst
  "psyker_smite_kill",
  "psyker_smite_stagger",
  -- Smite
  "psyker_protectorate_channel_chain_lightning_activated",
  -- Assail
  "psyker_throwing_knives",
  "psyker_throwing_knives_pierce",
  "psyker_throwing_knives_aimed",
  "psyker_throwing_knives_aimed_pierce",
}) do
  add_psykinetic_profile(name)
end

local function apply_preview_stats(self)
  if not State.enabled() then
    return
  end

  local stats = self._stat_buffs
  local data = runtime(self._unit)
  local now = FixedFrame.get_latest_fixed_time()

  -- Chorus pulse buffs may affect allies, not only the local player.
  if data.holy_cause_until and now < data.holy_cause_until and data.holy_cause_stacks and data.holy_cause_stacks > 0 then
    multiply_stat(stats, stat_buffs.toughness_damage_taken_multiplier, 0.92 ^ data.holy_cause_stacks)
  elseif data.holy_cause_until and now >= data.holy_cause_until then
    data.holy_cause_until = nil
    data.holy_cause_stacks = nil
  end

  if data.ecclesiarch_until and now < data.ecclesiarch_until and data.ecclesiarch_stacks and data.ecclesiarch_stacks > 0 then
    add_stat(stats, stat_buffs.damage, 0.06 * data.ecclesiarch_stacks)
  elseif data.ecclesiarch_until and now >= data.ecclesiarch_until then
    data.ecclesiarch_until = nil
    data.ecclesiarch_stacks = nil
  end

  if not is_local_player(self._player) then
    return
  end

  local class = class_key(self._player)

  if class == "zealot" then
    if State.has_node(class, NODE.zealot.wait_in_line) then
      multiply_stat(stats, stat_buffs.ranged_damage_taken_multiplier, 0.80)
    end
    if State.has_node(class, NODE.zealot.purifying_hatred) then
      add_stat(stats, stat_buffs.damage_vs_burning, 0.15)
      add_stat(stats, stat_buffs.damage_vs_electrocuted, 0.15)
    end

    if data.unkillable_until and now < data.unkillable_until then
      self._keywords[keywords.resist_death] = true
    end
  elseif class == "psyker" then
    if State.has_node(class, NODE.psyker.focused_warp) then
      add_stat(stats, stat_buffs.warp_damage, 0.15)
    end
  end
end

local function tick_preview_effects(self, unit, dt, t)
  if not State.enabled() or not self._is_server or not is_local_player(self._player) then
    return
  end

  local class = class_key(self._player)
  local data = runtime(unit)

  if class == "zealot" and State.has_node(class, NODE.zealot.voice_of_terra) then
    local unit_data = ScriptUnit.has_extension(unit, "unit_data_system")
    if unit_data then
      local shooting = unit_data:read_component("shooting_status")
      local is_shooting = shooting and (shooting.shooting or t <= shooting.shooting_end_time + 0.5)
      if is_shooting then
        Toughness.replenish_percentage(unit, 0.10 * dt, false, "depths_preview_voice_of_terra")
      end
    end
  end

  if class == "ogryn" and State.has_node(class, NODE.ogryn.found_some_more) then
    data.next_ammo_tick = data.next_ammo_tick or (t + 15)
    if t >= data.next_ammo_tick then
      Ammo.add_to_all_slots(unit, 0.01)
      data.next_ammo_tick = t + 15
    end
  else
    data.next_ammo_tick = nil
  end
end

local function handle_out_of_pocket(self, params)
  local unit = self._unit
  local unit_data = ScriptUnit.has_extension(unit, "unit_data_system")
  if not unit_data then
    return
  end

  local slot = unit_data:write_component("slot_secondary")
  if not slot then
    return
  end

  local missing = Ammo.missing_ammo_in_clips(slot)
  if missing <= 0 then
    return
  end

  Ammo.add_to_clip(slot, math.max(1, math.ceil(missing * 0.10)))
end

local function handle_got_your_back(self, params)
  local attacked_unit = params.attacked_unit
  local blackboard = attacked_unit and BLACKBOARDS[attacked_unit]
  local perception = blackboard and blackboard.perception
  local ally_unit = perception and perception.target_unit
  local self_unit = self._unit

  if not ally_unit or ally_unit == self_unit or not HEALTH_ALIVE[ally_unit] then
    return
  end

  local ally_toughness = ScriptUnit.has_extension(ally_unit, "toughness_system")
  if not ally_toughness then
    return
  end

  Toughness.replenish_percentage(ally_unit, 0.075, false, "depths_preview_got_your_back_ally")
  Toughness.replenish_percentage(self_unit, 0.05, false, "depths_preview_got_your_back_self")
end

local function handle_peril_equilibrium(self, params)
  local damage_type = params.damage_type
  local attack_type = params.attack_type

  if warp_damage_types[damage_type] then
    return
  end
  if attack_type ~= attack_types.melee and attack_type ~= attack_types.ranged then
    return
  end

  local unit = self._unit
  local unit_data = ScriptUnit.has_extension(unit, "unit_data_system")
  if not unit_data then
    return
  end

  local warp = unit_data:write_component("warp_charge")
  local current = warp.current_percentage or 0
  if current >= 0.75 then
    return
  end

  local amount = math.min(0.02, 0.75 - current)
  WarpCharge.increase_immediate(
    FixedFrame.get_latest_fixed_time(),
    1,
    warp,
    {
      psyker_smite = false,
      use_charge = false,
      warp_charge_percent = amount,
    },
    unit,
    1,
    true
  )
end

local function handle_proc_event(self, event, params)
  if not State.enabled() or not self._is_server or not is_local_player(self._player) then
    return
  end

  local class = class_key(self._player)
  local data = runtime(self._unit)

  if class == "zealot" then
    if event == proc_events.on_weapon_special_activate and State.has_node(class, NODE.zealot.holy_tools) then
      data.holy_tools_until = (params.t or FixedFrame.get_latest_fixed_time()) + 5
    elseif event == proc_events.on_sweep_start and State.has_node(class, NODE.zealot.holy_tools) then
      local t = FixedFrame.get_latest_fixed_time()
      if data.holy_tools_until and t <= data.holy_tools_until then
        local unit_data = ScriptUnit.has_extension(self._unit, "unit_data_system")
        local inventory = unit_data and unit_data:read_component("inventory")
        if inventory and inventory.wielded_slot == "slot_primary" then
          data.holy_tools_active_sweep = true
          data.holy_tools_until = nil
        end
      end
    elseif event == proc_events.on_sweep_finish then
      data.holy_tools_active_sweep = nil
    elseif event == proc_events.on_kill and params.attack_type == attack_types.melee then
      if State.has_node(class, NODE.zealot.out_of_pocket) then
        handle_out_of_pocket(self, params)
      end
      if State.has_node(class, NODE.zealot.got_your_back) then
        handle_got_your_back(self, params)
      end
    end

    -- Zealous Pilgrim: use the native combat-ability proc as the authoritative
    -- trigger for Chastise/Fury. Stealth/relic-specific stop events are refined
    -- by dedicated hooks below when available.
    if event == proc_events.on_combat_ability
      and State.has_node(class, NODE.zealot.zealous_pilgrim)
      and State.has_node(class, NODE.zealot.fury)
    then
      data.unkillable_until = FixedFrame.get_latest_fixed_time() + 5
    end
  elseif class == "psyker" then
    if event == proc_events.on_hit and State.has_node(class, NODE.psyker.peril_equilibrium) then
      handle_peril_equilibrium(self, params)
    end
  end
end

function Runtime.install()
  if installed then
    return
  end
  installed = true

  mod:hook_safe(BuffExtensionBase, "_update_stat_buffs_and_keywords", function(self)
    apply_preview_stats(self)
  end)

  mod:hook_safe("PlayerUnitBuffExtension", "fixed_update", function(self, unit, dt, t)
    tick_preview_effects(self, unit, dt, t)
  end)

  mod:hook_safe(BuffExtensionBase, "add_proc_event", function(self, event, params)
    handle_proc_event(self, event, params)
  end)

  mod:hook_safe(ActionZealotChannel, "_on_channel_tick", function(self, dt, in_coherence_units, t)
    local player = local_player()
    local class = class_key(player)
    if not State.enabled() or class ~= "zealot" or self._player_unit ~= (player and player.player_unit) then
      return
    end

    local holy_cause = State.has_node(class, NODE.zealot.holy_cause)
    local ecclesiarch = State.has_node(class, NODE.zealot.ecclesiarchs_call)
    if not holy_cause and not ecclesiarch then
      return
    end

    for unit, _ in pairs(in_coherence_units or {}) do
      local data = runtime(unit)
      if holy_cause then
        data.holy_cause_stacks = math.min(5, (data.holy_cause_stacks or 0) + 1)
        data.holy_cause_until = t + 10
      end
      if ecclesiarch then
        data.ecclesiarch_stacks = math.min(5, (data.ecclesiarch_stacks or 0) + 1)
        data.ecclesiarch_until = t + 10
      end
    end
  end)

  mod:hook_safe(ActionZealotChannel, "finish", function(self, reason, data, t)
    local player = local_player()
    local class = class_key(player)
    if State.enabled()
      and class == "zealot"
      and self._player_unit == (player and player.player_unit)
      and State.has_node(class, NODE.zealot.zealous_pilgrim)
      and State.has_node(class, NODE.zealot.chorus)
    then
      runtime(self._player_unit).unkillable_until = t + 5
    end
  end)

  mod:hook_safe(Buff, "destroy", function(self)
    local template_name = self:template_name()
    if template_name ~= "zealot_invisibility" and template_name ~= "zealot_invisibility_increased_duration" then
      return
    end

    local context = self:template_context()
    local unit = context and context.unit
    local player = local_player()
    local class = class_key(player)

    if State.enabled()
      and class == "zealot"
      and unit == (player and player.player_unit)
      and State.has_node(class, NODE.zealot.zealous_pilgrim)
      and State.has_node(class, NODE.zealot.shroudfield)
    then
      runtime(unit).unkillable_until = FixedFrame.get_latest_fixed_time() + 5
    end
  end)

  mod:hook(DamageCalculation, "calculate", function(func, damage_profile, damage_type, target_settings, lerp_values, hit_zone_name, power_level, charge_level, breed_or_nil, attacker_owner_breed_or_nil, attacker_breed_or_nil, is_critical_strike, hit_weakspot, hit_shield, is_backstab, is_flanking, dropoff_scalar, attack_type, attacker_stat_buffs, target_stat_buffs, attacker_buff_extension, target_buff_extension, armor_penetrating, target_health_extension, target_toughness_extension, armor_type, target_stagger_count, num_triggered_staggers, is_attacked_unit_suppressed, distance, target_unit, auto_completed_action, stagger_impact, stagger_impact_bonus, attacking_unit_or_nil, attacking_unit_owner_unit_or_nil, attacker_owner_buff_extension, target_index)
    local damage, efficiency, base_damage, base_buff_damage, rending_damage, finesse_boost_damage, backstab_damage, flanking_damage, armor_damage_modifier, hit_zone_damage_multiplier = func(
      damage_profile, damage_type, target_settings, lerp_values, hit_zone_name, power_level, charge_level,
      breed_or_nil, attacker_owner_breed_or_nil, attacker_breed_or_nil, is_critical_strike, hit_weakspot,
      hit_shield, is_backstab, is_flanking, dropoff_scalar, attack_type, attacker_stat_buffs, target_stat_buffs,
      attacker_buff_extension, target_buff_extension, armor_penetrating, target_health_extension,
      target_toughness_extension, armor_type, target_stagger_count, num_triggered_staggers,
      is_attacked_unit_suppressed, distance, target_unit, auto_completed_action, stagger_impact,
      stagger_impact_bonus, attacking_unit_or_nil, attacking_unit_owner_unit_or_nil,
      attacker_owner_buff_extension, target_index
    )

    if State.enabled() then
      local player = local_player()
      local unit = player and player.player_unit
      local attacker = attacking_unit_owner_unit_or_nil or attacking_unit_or_nil
      if unit and attacker == unit then
        local class = class_key(player)
        if class == "psyker" and State.has_node(class, NODE.psyker.psykinetic_grip) and psykinetic_profiles[damage_profile] then
          damage = damage * 1.20
        elseif class == "zealot" then
          local data = runtime(unit)
          if data.holy_tools_active_sweep and attack_type == attack_types.melee then
            damage = damage * 1.20
          end
        end
      end
    end

    return damage, efficiency, base_damage, base_buff_damage, rending_damage, finesse_boost_damage, backstab_damage, flanking_damage, armor_damage_modifier, hit_zone_damage_multiplier
  end)
end

function Runtime.clear()
  table.clear(runtime_by_unit)
end

return Runtime
