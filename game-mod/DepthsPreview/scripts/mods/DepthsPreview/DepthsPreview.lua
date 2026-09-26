local mod = get_mod("DepthsPreview")

local PlayerUnitTalentExtension = require("scripts/extension_systems/talent/player_unit_talent_extension")

local State = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_state")
local TalentUI = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_talent_ui")
local Equipment = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/preview_equipment")
local Balance = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/balance_preview")
local Blessings = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/blessing_preview")
local TalentBalance = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/talent_balance_preview")
local RuntimePreview = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/runtime_preview")

local function current_class()
  local player = Managers.player and Managers.player:local_player(1)
  local profile = player and player:profile()
  local archetype = profile and profile.archetype
  return archetype and archetype.name or nil
end

local function apply_preview_rules()
  Balance.apply()
  TalentBalance.apply()
  Blessings.apply()
  TalentUI.set_enabled(true)
end

local function restore_preview_rules()
  TalentUI.set_enabled(false)
  Blessings.restore()
  TalentBalance.restore()
  Balance.restore()
  RuntimePreview.clear()
end

local function apply_mode()
  TalentUI.install()
  RuntimePreview.install()
  Equipment.install()

  if State.enabled() then
    apply_preview_rules()
  else
    restore_preview_rules()
  end
end

function mod.open_preview()
  TalentUI.open()
end

function mod.toggle_preview()
  local next_value = not State.enabled()
  State.set_enabled(next_value)

  if next_value then
    apply_preview_rules()
    mod:notify("Depths Preview：体验服模式已开启")
  else
    restore_preview_rules()
    mod:notify("Depths Preview：已恢复正式服本地数据")
  end
end

local function print_weapon_list()
  local catalog = Equipment.catalog()
  mod:echo("体验武器 / Preview weapons:")
  for _, id in ipairs({
    "cruncher",
    "huntsman",
    "thugshot",
    "crusher_mk7",
    "double_barrel_mk4",
    "gromm_shield",
  }) do
    local entry = catalog[id]
    if entry then
      mod:echo(string.format("  %s -> %s", id, entry.zh or entry.display or id))
    end
  end
end

local function select_preview_weapon(id)
  if not id or id == "" or id == "list" then
    print_weapon_list()
    return
  end

  if id == "clear" then
    Equipment.clear()
    mod:echo("已清空当前职业的体验武器覆盖；下次生成本地玩家时恢复正式装备。")
    return
  end

  local ok, result = Equipment.select(id)
  if not ok then
    mod:echo(result or "无法选择体验武器")
    return
  end

  mod:echo(string.format(
    "已选择 %s。该武器会在下一次进入/重新生成 SoloPlay 或 Realms 本地主机角色时装入。",
    result.zh or result.display or id
  ))
  mod:echo("注意：9 月 27 日客户端尚无正式新武器资源，因此当前是机制/同家族原型，不冒充最终模型和动画。")
end

local function print_status()
  local class_key, count = TalentUI.status()
  local equipment_class, loadout = Equipment.selection()
  local blessing = Blessings.status()

  mod:echo(string.format(
    "Depths Preview | enabled=%s | class=%s | selected talents=%d",
    tostring(State.enabled()),
    tostring(class_key),
    count or 0
  ))

  if equipment_class then
    mod:echo(string.format(
      "Preview loadout | primary=%s | secondary=%s",
      tostring(loadout.slot_primary or "-"),
      tostring(loadout.slot_secondary or "-")
    ))
  end

  mod:echo(string.format(
    "Blessings | Counterattack runtime=%d overrides=%d | Energy Transfer runtime=%d overrides=%d | Lightning Reflexes=%s",
    blessing.counterattack_runtime or 0,
    blessing.counterattack_overrides or 0,
    blessing.energy_transfer_runtime or 0,
    blessing.energy_transfer_overrides or 0,
    tostring(blessing.lightning_reflexes)
  ))
end

local function run_selftest()
  local passed = 0
  local failed = 0

  local function report(ok, name, detail)
    if ok then
      passed = passed + 1
      mod:echo(string.format("[PASS] %s%s", name, detail and (" | " .. detail) or ""))
    else
      failed = failed + 1
      mod:echo(string.format("[FAIL] %s%s", name, detail and (" | " .. detail) or ""))
    end
  end

  local trees = TalentUI.selftest()
  for _, class_key in ipairs({ "veteran", "zealot", "psyker", "ogryn" }) do
    local item = trees[class_key]
    report(
      item and item.ok,
      "Talent tree " .. class_key,
      item and string.format("%d/%d nodes", item.layout_nodes, item.expected_nodes) or "missing"
    )
  end

  local weapons = Equipment.selftest()
  for _, id in ipairs({
    "cruncher",
    "huntsman",
    "thugshot",
    "crusher_mk7",
    "double_barrel_mk4",
    "gromm_shield",
  }) do
    report(weapons[id] == true, "Preview weapon " .. id)
  end

  local blessing = Blessings.status()
  report(
    (blessing.counterattack_runtime or 0) > 0,
    "Counterattack templates",
    tostring(blessing.counterattack_runtime or 0)
  )
  report(
    (blessing.energy_transfer_runtime or 0) > 0,
    "Energy Transfer templates",
    tostring(blessing.energy_transfer_runtime or 0)
  )
  report(
    blessing.lightning_reflexes == "split-trigger-active",
    "Lightning Reflexes split trigger",
    tostring(blessing.lightning_reflexes)
  )

  mod:echo(string.format("Depths Preview self-test: %d PASS / %d FAIL", passed, failed))
end

mod.on_all_mods_loaded = function()
  apply_mode()
end

mod:command("depths", "Standalone Depths of the Damned local preview environment", function(action, arg)
  action = string.lower(action or "open")
  arg = arg and string.lower(arg) or nil

  if action == "open" then
    mod.open_preview()
  elseif action == "on" then
    State.set_enabled(true)
    apply_preview_rules()
    mod:echo("Depths Preview 已开启；天赋页现在使用体验服树。")
  elseif action == "off" then
    State.set_enabled(false)
    restore_preview_rules()
    mod:echo("Depths Preview 已关闭；已恢复原版天赋树、祝福模板和角色正式天赋。")
  elseif action == "reset" then
    local class_key = current_class()
    if class_key then
      State.clear_selection(class_key)
      TalentUI.apply_selection(class_key, {})
      mod:echo("已清空当前职业的体验服天赋。")
    end
  elseif action == "weapon" then
    select_preview_weapon(arg)
  elseif action == "status" then
    print_status()
  elseif action == "selftest" then
    run_selftest()
  else
    mod:echo("用法：/depths open | on | off | reset | status | selftest | weapon <list|clear|id>")
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
