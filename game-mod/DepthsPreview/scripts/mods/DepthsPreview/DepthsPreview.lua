local mod = get_mod("DepthsPreview")

local PlayerUnitTalentExtension = require("scripts/extension_systems/talent/player_unit_talent_extension")

local State = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_state")
local TalentUI = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_talent_ui")
local Balance = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/balance_preview")

local function current_class()
  local player = Managers.player and Managers.player:local_player(1)
  local profile = player and player:profile()
  local archetype = profile and profile.archetype
  return archetype and archetype.name or nil
end

local function apply_mode()
  TalentUI.install()
  if State.enabled() then
    Balance.apply()
    TalentUI.set_enabled(true)
  else
    Balance.restore()
    TalentUI.set_enabled(false)
  end
end

function mod.open_preview()
  TalentUI.open()
end

function mod.toggle_preview()
  local next_value = not State.enabled()
  State.set_enabled(next_value)
  if next_value then
    Balance.apply()
    TalentUI.set_enabled(true)
    mod:notify("Depths Preview：体验服模式已开启")
  else
    TalentUI.set_enabled(false)
    Balance.restore()
    mod:notify("Depths Preview：已恢复正式服本地数据")
  end
end

mod.on_all_mods_loaded = function()
  apply_mode()
end

mod:command("depths", "Open the standalone Depths Preview talent page", function(action)
  action = string.lower(action or "open")

  if action == "open" then
    mod.open_preview()
  elseif action == "on" then
    State.set_enabled(true)
    Balance.apply()
    TalentUI.set_enabled(true)
    mod:echo("Depths Preview 已开启；天赋页现在使用体验服树。")
  elseif action == "off" then
    TalentUI.set_enabled(false)
    Balance.restore()
    mod:echo("Depths Preview 已关闭；已恢复原版天赋树与正式角色天赋。")
  elseif action == "reset" then
    local class_key = current_class()
    if class_key then
      State.clear_selection(class_key)
      TalentUI.apply_selection(class_key, {})
      mod:echo("已清空当前职业的体验服天赋。")
    end
  elseif action == "status" then
    local class_key, count = TalentUI.status()
    mod:echo(string.format(
      "Depths Preview | enabled=%s | class=%s | selected=%d",
      tostring(State.enabled()),
      tostring(class_key),
      count or 0
    ))
  else
    mod:echo("用法：/depths open | on | off | reset | status")
  end
end)

mod:hook(PlayerUnitTalentExtension, "game_object_initialized", function(func, self, game_object_id)
  func(self, game_object_id)

  if not State.enabled() then
    return
  end

  local player = self._player
  if not player or player.remote then
    return
  end

  local profile = player:profile()
  local class_key = profile and profile.archetype and profile.archetype.name
  if not class_key then
    return
  end

  TalentUI.apply_selection(class_key, State.selection(class_key))
end)
