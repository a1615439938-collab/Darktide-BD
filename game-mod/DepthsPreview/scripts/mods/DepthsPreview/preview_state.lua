local mod = get_mod("DepthsPreview")

local State = {
  _enabled = true,
  _selections = {},
  _loadout = {},
}

local function clone(value)
  if type(value) ~= "table" then
    return value
  end
  local out = {}
  for k, v in pairs(value) do
    out[clone(k)] = clone(v)
  end
  return out
end

function State.load()
  local enabled = mod:get("_preview_enabled")
  State._enabled = enabled == nil and true or enabled ~= false

  local selections = mod:get("_preview_talent_selections")
  if type(selections) == "table" then
    State._selections = clone(selections)
  end

  local loadout = mod:get("_preview_loadout")
  if type(loadout) == "table" then
    State._loadout = clone(loadout)
  end
end

function State.enabled()
  return State._enabled
end

function State.set_enabled(value)
  State._enabled = value ~= false
  mod:set("_preview_enabled", State._enabled, false)
end

function State.has_node(class_key, widget_name)
  local selected = State._selections[class_key]
  local tier = selected and selected[widget_name]
  return tier ~= nil and tier > 0
end

function State.selection(class_key)
  return clone(State._selections[class_key] or {})
end

function State.set_selection(class_key, node_tiers)
  State._selections[class_key] = clone(node_tiers or {})
  mod:set("_preview_talent_selections", State._selections, false)
end

function State.clear_selection(class_key)
  State._selections[class_key] = {}
  mod:set("_preview_talent_selections", State._selections, false)
end

function State.loadout(class_key)
  return clone(State._loadout[class_key] or {})
end

function State.set_loadout(class_key, loadout)
  State._loadout[class_key] = clone(loadout or {})
  mod:set("_preview_loadout", State._loadout, false)
end

State.load()

return State
