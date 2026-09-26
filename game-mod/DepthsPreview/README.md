# DepthsPreview — 独立本地体验服

这是一个**完全独立于 darktide-bd 网站**的 Darktide Mod。仓库只作为代码存放位置；运行时不读取网站、`tree-core.js` 或网页导出码。

目标是在 2026-09-29 `Depths of the Damned` 正式更新前，尽可能把 Fatshark 已公开的四个基础职业新天赋树、基础数值、部分祝福和平衡改动带进 9 月 27 日客户端，并通过 SoloPlay / Realms 本地主机试玩。

## 目前能做什么

### 1. 直接在游戏里点新版天赋

- Veteran：77 节点
- Zealot：83 节点
- Psyker：82 节点
- Ogryn：87 节点
- 使用 Darktide 原生 `TalentBuilderView`，不是网页或仿制 UI。
- 原生连线、30 点预算、鼠标/手柄操作继续由游戏 UI 负责。
- Blitz / Aura / Combat Ability / 底部主 Keystone 已按预览树设置互斥。
- `/depths open` 会直接切到原生天赋页。

能与当前客户端安全对应的节点直接复用 Fatshark 当前实现；改过数值/触发的节点在 Preview 层覆盖；真正新增节点由 `runtime_preview.lua` 实现。

### 2. 已实现的预览天赋改动

除了大量可直接复用的现有节点外，Preview 层已覆盖下列重点变化/新增机制：

**Veteran**
- Survivalist
- Deadshot
- Close and Kill
- Duty and Honour
- Duck and Dive

**Zealot**
- Chorus of Spiritual Fortitude（5 pulse / 预览半径）
- Until Death
- Holy Revenant
- Holy Cause
- Ecclesiarch's Call
- Zealous Pilgrim
- Fire And Fury
- Risen
- Faithful Frenzy
- Retributor's Stance
- Unseen Blade
- The Voice Of Terra
- Out Of Pocket
- Wait In Line
- Holy Tools
- Got Your Back
- Purifying Hatred

**Psyker**
- Perilous Combustion
- Psykinetic's Aura
- Mind in Motion
- Surety of Arms
- Focused Warp
- Peril Equilibrium
- Psykinetic Grip

**Ogryn**
- Soften Them Up
- Maximum Firepower
- Bruiser
- Dominate
- Indomitable
- Go Again!
- Keep Shooting
- Found Some More
- 预览树对应的 Toughness Damage Reduction 数值修正

### 3. 基础职业数值

- Veteran Base Toughness：120
- Zealot Base Toughness：125
- Ogryn Base Toughness：125
- Psyker Base Critical Chance：10%
- Veteran Stamina Regen Delay：0.5 s

### 4. 已实现的祝福预览

- **Counterattack**：普通 Block 触发；6 s；可刷新。
- **Energy Transfer**：普通 Block 触发并可刷新。
- **Lightning Reflexes**：普通 Block 触发力量部分；Perfect Block 仍负责眩晕。

Preview 关闭时会恢复原模板。

### 5. 新武器原型

Fatshark 已公开 9 月 29 日的六项新武器 / Mark：

- Ogryn Cruncher
- Huntsman's Shotgun
- Ogryn Thugshot
- Crusher Krourk Mk VII
- Double-Barrelled Shotgun Krourk Mk IV
- Gromm Mk I Battle Maul & Mk V Slab Shield

**重要限制：2026-09-27 客户端还没有这些正式新武器的完整 weapon template、模型和动画资源。**

因此本 Mod 当前使用已存在的同家族/近似武器资源作为本地可玩原型。它们不会被描述成“官方最终武器”。正式资源进入客户端后才能做到完全一致的模型、动画和 moveset。

选择命令：

```
/depths weapon list
/depths weapon cruncher
/depths weapon huntsman
/depths weapon thugshot
/depths weapon crusher_mk7
/depths weapon double_barrel_mk4
/depths weapon gromm_shield
/depths weapon clear
```

体验武器只覆盖本地任务生成时的 runtime loadout，不创建假后端库存物品。

## 正式账号隔离

Preview 模式会：

- 拦截体验天赋写入 Fatshark 正式角色后端。
- 把 Preview 天赋保存到 DMF 本地设置。
- 仅在 SoloPlay / Realms 的本地服务器权威环境应用战斗效果。
- Preview 武器只在本地玩家生成时覆盖 runtime loadout。
- `/depths off` 恢复原天赋布局、正式角色天赋、祝福模板和基础数值。

不要把它当作官方服务器上的客户端作弊 Mod 使用；设计目标就是 SoloPlay / Realms 本地体验服。

## 安装

需要：

1. Darktide Mod Loader
2. Darktide Mod Framework (DMF)
3. SoloPlay 或 Realms Server（实际战斗试玩）

把整个：

```
game-mod/DepthsPreview
```

复制成：

```
<Darktide>/mods/DepthsPreview
```

最终应类似：

```
<Darktide>/mods/DepthsPreview/DepthsPreview.mod
<Darktide>/mods/DepthsPreview/info.json
<Darktide>/mods/DepthsPreview/scripts/mods/DepthsPreview/DepthsPreview.lua
...
```

然后在：

```
<Darktide>/mods/mod_load_order.txt
```

加入一行：

```
DepthsPreview
```

## 第一次启动建议

进游戏后依次运行：

```
/depths on
/depths selftest
/depths open
```

`/depths selftest` 会检查：

- 四职业 Preview 树节点是否完整（77 / 83 / 82 / 87）
- 六个武器原型依赖的当前客户端物品是否存在
- Counterattack
- Energy Transfer
- Lightning Reflexes

结果应显示 `PASS`；若有 `FAIL`，不要进入任务，先查看 Darktide 日志。

其他命令：

```
/depths status
/depths reset
/depths off
```

## 精度说明

本项目区分三档：

1. **Native reuse**：当前客户端已有完全相同机制，直接复用。
2. **Preview implementation**：按 Fatshark 公布的新数值/触发条件修改现有实现或加入本地 runtime 逻辑。
3. **Prototype / approximation**：Fatshark 未公布必要数值，或对应正式资源尚未下发。代码中会明确注明，不把猜测包装成官方实现。

例如 Holy Revenant 的击退范围、尚未下发的六把新武器模型/动画属于第 3 类。

## 数据来源

规则快照记录在：

`scripts/mods/DepthsPreview/official_preview_spec.lua`

主要依据 Fatshark 的：

- `PREVIEW - Upcoming Balance Changes`
- `New, Free Update Depths of the Damned Coming September 29`
- 随后发布的官方平衡修订

当前目标版本：**2026-09-29**。
