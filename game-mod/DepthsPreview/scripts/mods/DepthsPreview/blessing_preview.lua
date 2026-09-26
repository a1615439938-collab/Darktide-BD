local mod = get_mod("DepthsPreview")

local BuffTemplates = require("scripts/settings/buff/buff_templates")
local BuffSettings = require("scripts/settings/buff/buff_settings")

local BlessingPreview = {}
local proc_events = BuffSettings.proc_events
local originals = {}
local applied = false

local TRAIT_PATHS = {
  "scripts/settings/equipment/weapon_traits/weapon_traits_bespoke_powersword_p2",
  "scripts/settings/equipment/weapon_traits/weapon_traits_bespoke_powersword_2h_p1",
  "scripts/settings/equipment/weapon_traits/weapon_traits_bespoke_powermaul_shield_p1",
}

local function capture_table(target, fields)
  if originals[target] then
    return
  end
  local snapshot = {}
  for i = 1, #fields do
    local key = fields[i]
    if type(target[key]) == "table" then
      snapshot[key] = table.deep_clone and table.deep_clone(target[key]) or table.clone(target[key])
    else
      snapshot[key] = target[key]
    end
  end
  originals[target] = snapshot
end

local function restore_table(target, snapshot)
  for key, value in pairs(snapshot) do
    if type(value) == "table" then
      target[key] = table.deep_clone and table.deep_clone(value) or table.clone(value)
    else
      target[key] = value
    end
  end
end

local function change_trigger(template, duration, refresh)
  if not template or type(template) ~= "table" then
    return false
  end

  capture_table(template, {
    "proc_events",
    "active_duration",
    "allow_proc_while_active",
  })

  template.proc_events = template.proc_events or {}
  template.proc_events[proc_events.on_perfect_block] = nil
  template.proc_events[proc_events.on_block] = 1

  if duration then
    template.active_duration = duration
  end
  if refresh ~= nil then
    template.allow_proc_while_active = refresh
  end

  return true
end

local function patch_runtime_templates()
  local counterattack = 0
  local energy_transfer = 0

  for name, template in pairs(BuffTemplates) do
    if string.find(name, "attack_speed_on_perfect_block", 1, true) then
      if change_trigger(template, 6, true) then
        counterattack = counterattack + 1
      end
    elseif string.find(name, "slower_heat_buildup_on_perfect_block", 1, true) then
      if change_trigger(template, nil, true) then
        energy_transfer = energy_transfer + 1
      end
    end
  end

  return counterattack, energy_transfer
end

local function patch_trait_overrides()
  local counterattack = 0
  local energy_transfer = 0

  for i = 1, #TRAIT_PATHS do
    local path = TRAIT_PATHS[i]
    local traits = require(path)

    for name, definition in pairs(traits) do
      local is_counterattack = string.find(name, "attack_speed_on_perfect_block", 1, true) ~= nil
      local is_energy_transfer = string.find(name, "slower_heat_buildup_on_perfect_block", 1, true) ~= nil

      if (is_counterattack or is_energy_transfer) and definition.buffs then
        capture_table(definition, { "buffs" })

        for buff_name, tiers in pairs(definition.buffs) do
          if type(tiers) == "table" then
            for tier = 1, #tiers do
              local override = tiers[tier]
              if type(override) == "table" then
                if is_counterattack then
                  override.active_duration = 6
                  override.allow_proc_while_active = true
                elseif is_energy_transfer then
                  override.allow_proc_while_active = true
                end

                if override.proc_events then
                  override.proc_events[proc_events.on_perfect_block] = nil
                  override.proc_events[proc_events.on_block] = 1
                end
              end
            end
          end
        end

        if is_counterattack then
          counterattack = counterattack + 1
        else
          energy_transfer = energy_transfer + 1
        end
      end
    end
  end

  return counterattack, energy_transfer
end

function BlessingPreview.apply()
  if applied then
    return BlessingPreview.status()
  end

  local runtime_counterattack, runtime_energy = patch_runtime_templates()
  local override_counterattack, override_energy = patch_trait_overrides()

  applied = true
  BlessingPreview._status = {
    counterattack_runtime = runtime_counterattack,
    counterattack_overrides = override_counterattack,
    energy_transfer_runtime = runtime_energy,
    energy_transfer_overrides = override_energy,
    lightning_reflexes = "pending-split-trigger",
  }

  return BlessingPreview._status
end

function BlessingPreview.restore()
  for target, snapshot in pairs(originals) do
    restore_table(target, snapshot)
  end
  table.clear(originals)
  applied = false
  BlessingPreview._status = nil
end

function BlessingPreview.status()
  return BlessingPreview._status or {
    counterattack_runtime = 0,
    counterattack_overrides = 0,
    energy_transfer_runtime = 0,
    energy_transfer_overrides = 0,
    lightning_reflexes = "pending-split-trigger",
  }
end

return BlessingPreview
