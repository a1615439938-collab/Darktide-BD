local mod = get_mod("DepthsPreview")

local FixedFrame = require("scripts/utilities/fixed_frame")
local MatchmakingConstants = require("scripts/settings/network/matchmaking_constants")
local PlayerUnitTalentExtension = require("scripts/extension_systems/talent/player_unit_talent_extension")
local PreviewData = mod:io_dofile("DepthsPreview/scripts/mods/DepthsPreview/future_data")

local HOST_TYPES = MatchmakingConstants.HOST_TYPES
local SCHEMA = PreviewData.schema

local session = {
  build = nil,
  active = false,
  last_report = nil,
}

local function trim(value)
  return (value or ""):match("^%s*(.-)%s*$")
end

local function normalize_name(value)
  value = string.lower(trim(value))
  value = string.gsub(value, "[%s%p]+", "")
  return value
end

local function safe_localize(key)
  if not key or key == "" then
    return nil
  end
  local ok, value = pcall(Localize, key)
  if ok and value and value ~= "" and value ~= key then
    return value
  end
  return nil
end

local function local_authority()
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

local function local_player()
  local player_manager = Managers.player
  return player_manager and player_manager:local_player(1) or nil
end

local function archetype_key(profile)
  local archetype = profile and profile.archetype
  if not archetype then
    return nil
  end
  local key = archetype.name or archetype.archetype_name
  if type(key) == "string" then
    key = string.lower(key)
    for _, supported in ipairs({ "veteran", "zealot", "psyker", "ogryn" }) do
      if key == supported or string.find(key, supported, 1, true) then
        return supported
      end
    end
  end
  return nil
end

local function parse_code(code)
  code = trim(code)
  local prefix, schema, class_key, indexes = string.match(code, "^([^:]+):([^:]+):([^:]+):(.*)$")
  if prefix ~= "DTP1" then
    return nil, "需要 DTP1 试玩代码 / Expected a DTP1 preview code"
  end
  if schema ~= SCHEMA then
    return nil, string.format("代码版本不匹配：%s ≠ %s / Schema mismatch", tostring(schema), tostring(SCHEMA))
  end

  local class_data = PreviewData.classes[class_key]
  if not class_data then
    return nil, "当前 Alpha 只支持 Veteran / Zealot / Psyker / Ogryn"
  end

  local selected = {}
  local seen = {}
  if indexes ~= "" then
    for part in string.gmatch(indexes, "[^,]+") do
      local index = tonumber(part)
      if not index or index < 1 or index > #class_data.nodes or index ~= math.floor(index) then
        return nil, "试玩代码包含无效节点索引 / Invalid node index in preview code"
      end
      if not seen[index] then
        selected[#selected + 1] = index
        seen[index] = true
      end
    end
  end
  table.sort(selected)

  return {
    schema = schema,
    class_key = class_key,
    selected = selected,
    raw = code,
  }
end

local function layout_candidates(profile)
  local archetype = profile and profile.archetype
  if not archetype or not archetype.talent_layout_file_path or not archetype.talents then
    return nil, "角色天赋布局不可用 / Archetype talent layout is unavailable"
  end

  local layout = require(archetype.talent_layout_file_path)
  local by_display = {}
  local by_dev_name = {}

  for i = 1, #(layout.nodes or {}) do
    local layout_node = layout.nodes[i]
    local talent_key = layout_node.talent
    local definition = talent_key and archetype.talents[talent_key]
    if definition then
      local display = safe_localize(definition.display_name)
      local display_key = display and normalize_name(display) or nil
      if display_key and display_key ~= "" then
        by_display[display_key] = by_display[display_key] or {}
        by_display[display_key][#by_display[display_key] + 1] = talent_key
      end

      local dev_name = definition.name
      local dev_key = dev_name and normalize_name(dev_name) or nil
      if dev_key and dev_key ~= "" then
        by_dev_name[dev_key] = by_dev_name[dev_key] or {}
        by_dev_name[dev_key][#by_dev_name[dev_key] + 1] = talent_key
      end
    end
  end

  return {
    by_display = by_display,
    by_dev_name = by_dev_name,
  }
end

local function choose_candidate(list, ordinal)
  if not list or #list == 0 then
    return nil
  end
  if #list == 1 then
    return list[1]
  end
  return list[math.min(math.max(ordinal or 1, 1), #list)]
end

local function resolve_reuse_node(node, candidates)
  local ordinal = node.live_ordinal or 1
  local names = {
    node.live_en,
    node.live_cn,
  }

  for i = 1, #names do
    local name = names[i]
    if name and name ~= "" then
      local key = normalize_name(name)
      local found = choose_candidate(candidates.by_display[key], ordinal)
      if found then
        return found, "localized-display"
      end
    end
  end

  local dev_key = node.live_en and normalize_name(node.live_en)
  if dev_key and dev_key ~= "" then
    local found = choose_candidate(candidates.by_dev_name[dev_key], ordinal)
    if found then
      return found, "definition-name"
    end
  end

  return nil
end

local function compile_build(profile, build)
  local class_data = PreviewData.classes[build.class_key]
  if not class_data then
    return nil, nil, "该职业没有 Preview 数据 / Missing class preview data"
  end

  local candidates, candidate_error = layout_candidates(profile)
  if not candidates then
    return nil, nil, candidate_error
  end

  local talents = {}
  local report = {
    selected = #build.selected,
    reused = 0,
    custom = 0,
    unresolved = 0,
    custom_names = {},
    unresolved_names = {},
    resolved = {},
  }

  for _, index in ipairs(build.selected) do
    local node = class_data.nodes[index]
    if node.mode == "reuse" then
      local talent_key, method = resolve_reuse_node(node, candidates)
      if talent_key then
        talents[talent_key] = 1
        report.reused = report.reused + 1
        report.resolved[#report.resolved + 1] = {
          preview = node.en,
          talent_key = talent_key,
          method = method,
        }
      else
        report.unresolved = report.unresolved + 1
        report.unresolved_names[#report.unresolved_names + 1] = node.en
      end
    else
      report.custom = report.custom + 1
      report.custom_names[#report.custom_names + 1] = node.en
    end
  end

  return talents, report
end

local function report_lines(report)
  if not report then
    return { "尚未编译试玩构筑 / No preview build has been compiled yet" }
  end

  local lines = {
    string.format(
      "选择 %d | 可直接复用 %d | 待自定义 %d | 映射失败 %d",
      report.selected or 0,
      report.reused or 0,
      report.custom or 0,
      report.unresolved or 0
    ),
  }

  if #(report.custom_names or {}) > 0 then
    lines[#lines + 1] = "待实现 / custom: " .. table.concat(report.custom_names, ", ")
  end
  if #(report.unresolved_names or {}) > 0 then
    lines[#lines + 1] = "映射失败 / unresolved: " .. table.concat(report.unresolved_names, ", ")
  end

  return lines
end

local function echo_report(report)
  for _, line in ipairs(report_lines(report)) do
    mod:echo(line)
  end
end

local function apply_to_player(player, quiet)
  if not session.build then
    if not quiet then
      mod:echo("请先用 /depths_import 导入网站生成的 DTP1 代码。")
    end
    return false
  end

  if not local_authority() then
    if not quiet then
      mod:echo("拒绝应用：当前客户端不是 SoloPlay / Realms 本地游戏服务器。")
    end
    return false
  end

  player = player or local_player()
  if not player then
    if not quiet then
      mod:echo("本地玩家尚未创建 / Local player is not ready")
    end
    return false
  end

  local profile = player:profile()
  local current_class = archetype_key(profile)
  if current_class ~= session.build.class_key then
    if not quiet then
      mod:echo(string.format(
        "职业不匹配：代码是 %s，当前角色是 %s / Class mismatch",
        session.build.class_key,
        tostring(current_class)
      ))
    end
    return false
  end

  local talents, report, compile_error = compile_build(profile, session.build)
  if not talents then
    if not quiet then
      mod:echo(compile_error or "无法编译试玩构筑 / Failed to compile preview build")
    end
    return false
  end

  session.last_report = report

  if report.unresolved > 0 then
    if not quiet then
      mod:echo("为避免错误天赋，存在映射失败时不会应用构筑。")
      echo_report(report)
    end
    return false
  end

  local player_unit = player.player_unit
  if not player_unit then
    if not quiet then
      mod:echo("玩家单位尚未生成；进入本地任务后会自动再次尝试。")
      echo_report(report)
    end
    return false
  end

  local talent_extension = ScriptUnit.has_extension(player_unit, "talent_system")
  if not talent_extension then
    if not quiet then
      mod:echo("找不到 talent_system；进入任务后会自动再次尝试。")
    end
    return false
  end

  talent_extension:select_new_talents(talents, FixedFrame.get_latest_fixed_time())
  session.active = true

  if not quiet then
    mod:echo("已应用本地试玩构筑。注意：待自定义节点目前不会产生效果。")
    echo_report(report)
  end
  return true
end

local function restore_profile_talents(quiet)
  local player = local_player()
  if player and player.player_unit then
    local profile = player:profile()
    local talent_extension = ScriptUnit.has_extension(player.player_unit, "talent_system")
    if talent_extension and profile and profile.talents then
      talent_extension:select_new_talents(profile.talents, FixedFrame.get_latest_fixed_time())
    end
  end
  session.active = false
  if not quiet then
    mod:echo("已恢复角色原有天赋 / Restored profile talents")
  end
end

mod:command("depths_import", mod:localize("command_import"), function(code)
  if not code or trim(code) == "" then
    mod:echo("用法 / Usage: /depths_import DTP1:...")
    return
  end

  local build, err = parse_code(code)
  if not build then
    mod:echo(err)
    return
  end

  session.build = build
  session.active = false
  session.last_report = nil
  mod:echo(string.format("已导入 %s：%d 个节点 / Imported preview build", build.class_key, #build.selected))
  apply_to_player(nil, false)
end)

mod:command("depths_apply", mod:localize("command_apply"), function()
  apply_to_player(nil, false)
end)

mod:command("depths_status", mod:localize("command_status"), function()
  if not session.build then
    mod:echo("未导入试玩构筑 / No preview build imported")
    return
  end
  mod:echo(string.format(
    "DepthsPreview %s | class=%s | active=%s",
    SCHEMA,
    session.build.class_key,
    tostring(session.active)
  ))
  echo_report(session.last_report)
end)

mod:command("depths_off", mod:localize("command_off"), function()
  restore_profile_talents(false)
end)

mod:hook(PlayerUnitTalentExtension, "game_object_initialized", function(func, self, game_object_id)
  func(self, game_object_id)

  if not session.build or not local_authority() then
    return
  end

  local player = self._player
  if not player or player.remote then
    return
  end

  local profile = player:profile()
  if archetype_key(profile) ~= session.build.class_key then
    return
  end

  local talents, report = compile_build(profile, session.build)
  session.last_report = report
  if not talents or (report and report.unresolved > 0) then
    return
  end

  self:select_new_talents(talents, FixedFrame.get_latest_fixed_time())
  session.active = true
end)
