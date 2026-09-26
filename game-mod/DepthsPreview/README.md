# DepthsPreview — 独立本地体验服

目标不是网站联动，而是在 **当前 Darktide 客户端内**尽可能复现 2026-09-29
`Depths of the Damned` 更新，让玩家在正式更新前通过 SoloPlay / Realms 本地主机试玩。

## 设计原则

- 直接使用 Darktide 原生 TalentBuilderView：在游戏里点新版天赋。
- Preview 天赋选择只保存在 DMF 本地设置，不写 Fatshark 正式后端。
- 退出体验模式后恢复原版天赋树与角色正式天赋。
- 战斗效果只在本机拥有游戏服务器权威时应用（SoloPlay / Realms player host）。
- 官网已公布的改动按 Fatshark 预览和后续修订实现。
- 当前客户端不存在的全新武器资产不伪造成“官方资源”；先使用机制原型，正式资源下发后切换。

## 当前实现

### 游戏内新版天赋树
- Veteran / Zealot / Psyker / Ogryn 的 9 月 29 日预览树已固化到 Mod 自己的
  `preview_trees.lua`，运行时不读取网站文件。
- 注入游戏原生天赋页。
- 原生 30 点、路径、连线、互斥、鼠标/手柄交互继续由游戏 UI 处理。
- 能由当前客户端直接复用的节点使用当前 talent implementation。
- 真正改变机制/新增的节点使用独立 Preview talent ID，后续逐项实现，不静默套用旧效果。

### 正式后端隔离
Preview 模式下会拦截天赋页退出时的正式后端保存。选择保存在
`DepthsPreview` 本地状态，并在本地任务生成玩家时重新应用。

### 已应用基础数值
- Veteran Base Toughness: 120
- Zealot Base Toughness: 125
- Ogryn Base Toughness: 125
- Psyker Base Critical Chance: 10%
- Veteran Stamina Regen Delay: 0.5（后续官方修订）

## 操作

- `/depths open` — 打开游戏内配装/天赋界面
- `/depths on` — 开启体验服模式
- `/depths off` — 恢复原版树和角色正式天赋
- `/depths reset` — 清空当前职业 Preview 天赋
- `/depths status` — 查看状态

也可以在 DMF Mod 设置里使用“打开体验服配装”和“切换体验服模式”。

## 新武器

Fatshark 已公布 9 月 29 日六项新武器/Mark 内容。当前 9 月 27 日客户端源码快照
尚未包含对应的新模板/资源，因此分两阶段：

1. 现在：用已有武器家族构建机制原型，并实现已经公开的行为。
2. 正式资源进入客户端后：替换为官方 weapon template / model / animation。

规则快照见 `official_preview_spec.lua`。

## 官方资料

- Fatshark Forums: `PREVIEW - Upcoming Balance Changes`
- playdarktide.com: `New, Free Update Depths of the Damned Coming September 29`

## 安装

把整个 `DepthsPreview` 目录复制到 Darktide 的 mods 目录，并在
`mod_load_order.txt` 添加 `DepthsPreview`。

需要 Darktide Mod Loader + Darktide Mod Framework。
实际战斗试玩建议搭配 SoloPlay 或 Realms Server。
