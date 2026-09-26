local mod = get_mod("DepthsPreview")

local LocalizationManager = require("scripts/managers/localization/localization_manager")
local MasterItems = require("scripts/backend/master_items")
local MatchmakingConstants = require("scripts/settings/network/matchmaking_constants")
local UnitTemplate = require("scripts/extension_systems/unit_templates/utilities/unit_template")

local State = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_state")

local Equipment = {}
local HOST_TYPES = MatchmakingConstants.HOST_TYPES
local installed = false

local CATALOG = {
  cruncher = {
    display = "Ogryn Cruncher [Preview Prototype]",
    zh = "欧格林重型碎骨锤【体验原型】",
    class = { ogryn = true },
    slot = "slot_primary",
    source = "content/items/weapons/player/melee/ogryn_pickaxe_2h_p1_m1",
    fidelity = "mechanics-prototype",
  },
  huntsman = {
    display = "Huntsman's Shotgun [Preview Prototype]",
    zh = "猎手霰弹枪【体验原型】",
    class = { veteran=true, zealot=true, psyker=true, skitarii=true, hivescum=true },
    slot = "slot_secondary",
    source = "content/items/weapons/player/ranged/shotgun_p1_m2",
    fidelity = "mechanics-prototype",
  },
  thugshot = {
    display = "Ogryn Thugshot [Preview Prototype]",
    zh = "欧格林 Thugshot 独头弹霰弹枪【体验原型】",
    class = { ogryn = true },
    slot = "slot_secondary",
    source = "content/items/weapons/player/ranged/ogryn_thumper_p1_m1",
    fidelity = "mechanics-prototype",
  },
  crusher_mk7 = {
    display = "Crusher Krourk Mk VII [Preview Prototype]",
    zh = "Crusher Krourk Mk VII【体验原型】",
    class = { zealot=true, adamant=true },
    slot = "slot_primary",
    source = "content/items/weapons/player/melee/powermaul_2h_p1_m1",
    fidelity = "same-family-prototype",
  },
  double_barrel_mk4 = {
    display = "Double-Barrelled Shotgun Krourk Mk IV [Preview Prototype]",
    zh = "双管霰弹枪 Krourk Mk IV【体验原型】",
    class = { veteran=true, zealot=true, psyker=true, skitarii=true, hivescum=true, adamant=true },
    slot = "slot_secondary",
    source = "content/items/weapons/player/ranged/shotgun_p2_m1",
    fidelity = "same-family-prototype",
  },
  gromm_shield = {
    display = "Gromm Mk I Battle Maul & Mk V Slab Shield [Preview Prototype]",
    zh = "Gromm Mk I 战斗锤与 Mk V 盾牌【体验原型】",
    class = { ogryn = true },
    slot = "slot_primary",
    source = "content/items/weapons/player/melee/ogryn_powermaul_slabshield_p1_m1",
    fidelity = "same-family-prototype",
  },
}

local localization = {}
for id, entry in pairs(CATALOG) do
  localization["loc_depths_preview_weapon_" .. id] = { en=entry.display, zh=entry.zh }
end

local function chinese(manager)
  local language = string.lower(tostring(manager and manager:language() or ""))
  return string.find(language, "zh", 1, true) ~= nil or string.find(language, "chinese", 1, true) ~= nil
end

local function authority()
  local multiplayer_session = Managers.multiplayer_session
  if not multiplayer_session then
    return false
  end
  local host_type = multiplayer_session:host_type()
  if host_type ~= HOST_TYPES.singleplay and host_type ~= HOST_TYPES.player then
    return false
  end
  local game_session = Managers.state and Managers.state.game_session
  return game_session and game_session:is_server() or false
end

local function clone_master_item(entry)
  local master = MasterItems.get_item(entry.source)
  if not master then
    return nil
  end
  local item = table.clone(master)
  item.display_name = "loc_depths_preview_weapon_" .. entry.id
  item.depths_preview_prototype = true
  item.depths_preview_fidelity = entry.fidelity
  return item
end

local function class_key(player)
  local profile = player and player:profile()
  return profile and profile.archetype and profile.archetype.name or nil
end

function Equipment.catalog()
  local out = {}
  for id, data in pairs(CATALOG) do
    out[id] = data
  end
  return out
end

function Equipment.select(id)
  local entry = CATALOG[id]
  if not entry then
    return false, "未知体验武器 / Unknown preview weapon"
  end
  local player = Managers.player and Managers.player:local_player(1)
  local key = class_key(player)
  if key and not entry.class[key] then
    return false, "当前职业不能使用该体验武器 / Preview weapon is not available to this class"
  end

  local loadout = State.loadout(key or "unknown")
  loadout[entry.slot] = id
  State.set_loadout(key or "unknown", loadout)
  return true, entry
end

function Equipment.clear(slot)
  local player = Managers.player and Managers.player:local_player(1)
  local key = class_key(player)
  if not key then
    return
  end
  local loadout = State.loadout(key)
  if slot then
    loadout[slot] = nil
  else
    loadout = {}
  end
  State.set_loadout(key, loadout)
end

function Equipment.selection()
  local player = Managers.player and Managers.player:local_player(1)
  local key = class_key(player)
  return key, key and State.loadout(key) or {}
end

function Equipment.install()
  if installed then
    return
  end
  installed = true

  for id, entry in pairs(CATALOG) do
    entry.id = id
  end

  mod:hook(LocalizationManager, "localize", function(func, self, key, no_cache, context)
    local entry = localization[key]
    if entry then
      return chinese(self) and entry.zh or entry.en
    end
    return func(self, key, no_cache, context)
  end)

  mod:hook(UnitTemplate, "player_character_initial_items", function(func, game_mode_manager, profile, player)
    local items = func(game_mode_manager, profile, player)

    if not State.enabled() or player.remote or not authority() then
      return items
    end

    local key = profile and profile.archetype and profile.archetype.name
    local selection = key and State.loadout(key) or {}

    for slot, id in pairs(selection) do
      local entry = CATALOG[id]
      if entry and entry.slot == slot and entry.class[key] then
        local preview_item = clone_master_item(entry)
        if preview_item then
          items[slot] = preview_item
        end
      end
    end

    return items
  end)
end

return Equipment
