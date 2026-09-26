local mod = get_mod("DepthsPreview")

local Archetypes = require("scripts/settings/archetype/archetypes")
local FixedFrame = require("scripts/utilities/fixed_frame")
local InventoryBackgroundView = require("scripts/ui/views/inventory_background_view/inventory_background_view")
local LocalizationManager = require("scripts/managers/localization/localization_manager")
local TalentBuilderView = require("scripts/ui/views/talent_builder_view/talent_builder_view")
local TalentLayoutParser = require("scripts/ui/views/talent_builder_view/utilities/talent_layout_parser")

local PreviewTrees = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_trees")
local Compatibility = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/compatibility")
local State = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_state")

local TalentUI = {}

local NATIVE_LAYOUTS = {
  veteran = "scripts/ui/views/talent_builder_view/layouts/veteran_tree",
  zealot = "scripts/ui/views/talent_builder_view/layouts/zealot_tree",
  psyker = "scripts/ui/views/talent_builder_view/layouts/psyker_tree",
  ogryn = "scripts/ui/views/talent_builder_view/layouts/ogryn_tree",
}

local CATEGORY_TO_TYPE = {
  root = "start",
  passive = "default",
  stat = "stat",
  blitz = "tactical",
  aura = "aura",
  ability = "ability",
  abilmod = "ability_modifier",
  keystone = "keystone",
  keymod = "keystone_modifier",
}

local GENERIC_ICONS = {
  veteran = "content/ui/textures/icons/talents/veteran/veteran_default_general_talent",
  zealot = "content/ui/textures/icons/talents/zealot/zealot_default_general_talent",
  psyker = "content/ui/textures/icons/talents/psyker/psyker_default_general_talent",
  ogryn = "content/ui/textures/icons/talents/ogryn/ogryn_default_general_talent",
}

local original_layouts = {}
local preview_layouts = {}
local localization = {}
local installed = false

local function deep_copy(value, seen)
  if type(value) ~= "table" then
    return value
  end
  seen = seen or {}
  if seen[value] then
    return seen[value]
  end
  local out = {}
  seen[value] = out
  for k, v in pairs(value) do
    out[deep_copy(k, seen)] = deep_copy(v, seen)
  end
  return out
end

local function normalize(value)
  value = string.lower(tostring(value or ""))
  return (string.gsub(value, "[%s%p_]+", ""))
end

local function language_is_chinese(manager)
  local language = manager and manager:language() or ""
  language = string.lower(tostring(language))
  return string.find(language, "zh", 1, true) ~= nil or string.find(language, "chinese", 1, true) ~= nil
end

local function native_candidates(class_key, original_layout)
  local archetype = Archetypes[class_key]
  local result = {}
  for i = 1, #(original_layout.nodes or {}) do
    local layout_node = original_layout.nodes[i]
    local talent_key = layout_node.talent
    local definition = talent_key and archetype.talents[talent_key]
    if definition then
      local names = {}
      if definition.name then
        names[#names + 1] = definition.name
      end
      if definition.display_name then
        local ok, localized = pcall(Localize, definition.display_name)
        if ok and localized and localized ~= definition.display_name then
          names[#names + 1] = localized
        end
      end
      for j = 1, #names do
        local n = normalize(names[j])
        if n ~= "" then
          result[n] = result[n] or {}
          result[n][#result[n] + 1] = {
            talent = talent_key,
            node = layout_node,
            definition = definition,
          }
        end
      end
    end
  end
  return result
end

local function compatibility_by_slug(class_key)
  local out = {}
  local class_data = Compatibility.classes[class_key]
  for i = 1, #(class_data and class_data.nodes or {}) do
    local node = class_data.nodes[i]
    out[node.slug] = node
  end
  return out
end

local function choose_candidate(candidates, compatibility_node)
  if not candidates or #candidates == 0 then
    return nil
  end
  if #candidates == 1 then
    return candidates[1]
  end
  local ordinal = math.max(1, compatibility_node and compatibility_node.live_ordinal or 1)
  return candidates[math.min(ordinal, #candidates)]
end

local function resolve_native(lookup, compatibility_node)
  if not compatibility_node then
    return nil
  end
  for _, name in ipairs({
    compatibility_node.live_en,
    compatibility_node.live_cn,
  }) do
    if name and name ~= "" then
      local candidate = choose_candidate(lookup[normalize(name)], compatibility_node)
      if candidate then
        return candidate
      end
    end
  end
  return nil
end

local function custom_talent_key(class_key, snapshot_node)
  return "depths_preview_" .. class_key .. "_" .. string.gsub(snapshot_node.id, "^dp_", "")
end

local function loc_key(kind, class_key, snapshot_node)
  return "loc_depths_preview_" .. kind .. "_" .. class_key .. "_" .. string.gsub(snapshot_node.id, "^dp_", "")
end

local function register_custom_definition(class_key, snapshot_node, native_match)
  local archetype = Archetypes[class_key]
  local key = custom_talent_key(class_key, snapshot_node)
  local name_key = loc_key("name", class_key, snapshot_node)
  local desc_key = loc_key("desc", class_key, snapshot_node)

  localization[name_key] = {
    en = snapshot_node.en or key,
    zh = snapshot_node.cn ~= "" and snapshot_node.cn or snapshot_node.en or key,
  }
  localization[desc_key] = {
    en = snapshot_node.desc or "",
    zh = snapshot_node.desc_cn ~= "" and snapshot_node.desc_cn or snapshot_node.desc or "",
  }

  local icon = native_match and native_match.node and native_match.node.icon or GENERIC_ICONS[class_key]
  archetype.talents[key] = archetype.talents[key] or {
    description = desc_key,
    display_name = name_key,
    icon = icon,
    name = snapshot_node.en or key,
  }

  return key, icon
end

local function exclusive_groups(snapshot)
  local groups = {}
  local categories = {
    blitz = "blitz",
    aura = "aura",
    ability = "combat",
    keystone = "keystone",
  }

  for category, prefix in pairs(categories) do
    local list = {}
    for i = 1, #snapshot.nodes do
      local node = snapshot.nodes[i]
      if node.cat == category then
        list[#list + 1] = node
      end
    end
    table.sort(list, function(a, b)
      return a.y < b.y
    end)

    local group = 0
    local last_y = -999999
    for i = 1, #list do
      local node = list[i]
      if node.y - last_y > 90 then
        group = group + 1
      end
      last_y = node.y
      groups[node.slug] = "depths_preview_" .. prefix .. "_" .. tostring(group)
    end
  end

  return groups
end

local function build_layout(class_key, original_layout)
  local snapshot = PreviewTrees.classes[class_key]
  local compatibility = compatibility_by_slug(class_key)
  local candidates = native_candidates(class_key, original_layout)
  local exclusive = exclusive_groups(snapshot)

  local by_slug = {}
  local nodes = {}
  local max_y = 0
  local native_start

  for i = 1, #(original_layout.nodes or {}) do
    if original_layout.nodes[i].type == "start" then
      native_start = original_layout.nodes[i]
      break
    end
  end

  for i = 1, #snapshot.nodes do
    local source = snapshot.nodes[i]
    local compatibility_node = compatibility[source.slug]
    local native_match = resolve_native(candidates, compatibility_node)
    local is_root = source.cat == "root"
    local is_reuse = compatibility_node and compatibility_node.mode == "reuse" and native_match ~= nil

    local talent
    local icon

    if is_root and native_start then
      talent = native_start.talent
      icon = native_start.icon
    elseif is_reuse then
      talent = native_match.talent
      icon = native_match.node.icon
    else
      talent, icon = register_custom_definition(class_key, source, native_match)
    end

    local requirements = {
      all_parents_chosen = false,
      children_unlock_points = is_root and 0 or 1,
      min_points_spent = 0,
    }

    if exclusive[source.slug] then
      requirements.exclusive_group = exclusive[source.slug]
    elseif native_match and native_match.node and native_match.node.requirements then
      requirements.exclusive_group = native_match.node.requirements.exclusive_group
      requirements.incompatible_talent = native_match.node.requirements.incompatible_talent
    end

    -- Fatshark preview explicitly makes these alternatives.
    if class_key == "zealot" and (source.en == "Holy Revenant" or source.en == "Zealous Pilgrim") then
      requirements.exclusive_group = "depths_preview_zealot_unkillable_branch"
    end

    local node = {
      cost = is_root and 0 or 1,
      icon = icon or GENERIC_ICONS[class_key],
      max_points = 1,
      talent = talent,
      type = CATEGORY_TO_TYPE[source.cat] or "default",
      widget_name = source.id,
      x = math.floor(source.x + 180),
      y = math.floor(source.y * 1.35 - 50),
      children = {},
      parents = {},
      connector_offset = { 0, is_root and 42 or 0 },
      requirements = requirements,
    }

    max_y = math.max(max_y, node.y)
    nodes[#nodes + 1] = node
    by_slug[source.slug] = node
  end

  for i = 1, #snapshot.edges do
    local edge = snapshot.edges[i]
    local a = by_slug[edge[1]]
    local b = by_slug[edge[2]]
    if a and b then
      a.children[#a.children + 1] = b.widget_name
      b.parents[#b.parents + 1] = a.widget_name
    end
  end

  return {
    archetype_name = class_key,
    background_height = math.max(2600, max_y + 350),
    name = "depths_preview_" .. class_key,
    node_points = snapshot.budget or 30,
    talent_points = snapshot.budget or 30,
    version = 20260929,
    nodes = nodes,
  }
end

local function replace_table(target, source)
  table.clear(target)
  for k, v in pairs(source) do
    target[k] = v
  end
end

local function install_layouts()
  for class_key, path in pairs(NATIVE_LAYOUTS) do
    local native_layout = require(path)
    if not original_layouts[class_key] then
      original_layouts[class_key] = deep_copy(native_layout)
    end
    preview_layouts[class_key] = build_layout(class_key, original_layouts[class_key])
    replace_table(native_layout, preview_layouts[class_key])
  end
end

local function restore_layouts()
  for class_key, path in pairs(NATIVE_LAYOUTS) do
    local native_layout = require(path)
    local original = original_layouts[class_key]
    if original then
      replace_table(native_layout, deep_copy(original))
    end
  end
end

local function class_key_from_player(player)
  local profile = player and player:profile()
  local archetype = profile and profile.archetype
  local key = archetype and archetype.name
  return NATIVE_LAYOUTS[key] and key or nil
end

local function local_player()
  return Managers.player and Managers.player:local_player(1) or nil
end

local function selected_talents(class_key, node_tiers)
  local archetype = Archetypes[class_key]
  local layout = preview_layouts[class_key]
  local talents = table.shallow_copy(archetype.base_talents or {})
  TalentLayoutParser.selected_talents_from_selected_nodes(layout, node_tiers or {}, talents)
  return talents
end

function TalentUI.apply_selection(class_key, node_tiers)
  if not State.enabled() then
    return false
  end

  local player = local_player()
  if not player or class_key_from_player(player) ~= class_key or not player.player_unit then
    return false
  end

  local talent_extension = ScriptUnit.has_extension(player.player_unit, "talent_system")
  if not talent_extension then
    return false
  end

  talent_extension:select_new_talents(
    selected_talents(class_key, node_tiers),
    FixedFrame.get_latest_fixed_time()
  )
  return true
end

function TalentUI.restore_profile_talents()
  local player = local_player()
  if not player or not player.player_unit then
    return
  end
  local profile = player:profile()
  local talent_extension = ScriptUnit.has_extension(player.player_unit, "talent_system")
  if talent_extension and profile and profile.talents then
    talent_extension:select_new_talents(profile.talents, FixedFrame.get_latest_fixed_time())
  end
end

function TalentUI.set_enabled(value)
  State.set_enabled(value)
  if State.enabled() then
    install_layouts()
  else
    restore_layouts()
    TalentUI.restore_profile_talents()
  end
end

function TalentUI.open()
  if not State.enabled() then
    TalentUI.set_enabled(true)
  end
  if Managers.ui and not Managers.ui:view_active("inventory_background_view") then
    Managers.ui:open_view("inventory_background_view", nil, nil, nil, nil, nil)
  end
end

function TalentUI.status()
  local player = local_player()
  local class_key = class_key_from_player(player)
  local selection = class_key and State.selection(class_key) or {}
  local count = 0
  for _, tier in pairs(selection) do
    if tier and tier > 0 then
      count = count + 1
    end
  end
  return class_key, count
end

function TalentUI.install()
  if installed then
    return
  end
  installed = true

  if State.enabled() then
    install_layouts()
  end

  mod:hook(LocalizationManager, "localize", function(func, self, key, no_cache, context)
    local entry = localization[key]
    if entry then
      return language_is_chinese(self) and entry.zh or entry.en
    end
    return func(self, key, no_cache, context)
  end)

  mod:hook(TalentBuilderView, "on_enter", function(func, self)
    if State.enabled() then
      local class_key = class_key_from_player(self._preview_player)
      if class_key then
        self._context = self._context or {}
        self._context.current_profile_equipped_talents = State.selection(class_key)
      end
    end
    return func(self)
  end)

  mod:hook(InventoryBackgroundView, "_save_current_talents_to_profile_preset", function(func, self)
    if State.enabled() then
      return
    end
    return func(self)
  end)

  mod:hook(InventoryBackgroundView, "_apply_current_talents_to_profile", function(func, self)
    if State.enabled() then
      return
    end
    return func(self)
  end)

  mod:hook(InventoryBackgroundView, "event_player_talent_node_updated", function(func, self, node_tiers)
    local result = func(self, node_tiers)
    if State.enabled() then
      local class_key = class_key_from_player(self._preview_player)
      if class_key then
        State.set_selection(class_key, node_tiers)
        TalentUI.apply_selection(class_key, node_tiers)
      end
    end
    return result
  end)
end

return TalentUI
