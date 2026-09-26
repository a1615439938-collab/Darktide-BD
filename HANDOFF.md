# Darktide-BD Handoff / 项目交接

> 更新时间 / Updated: 2026-09-27  
> 仓库 / Repository: `a1615439938-collab/Darktide-BD`  
> 默认分支 / Default branch: `main`

## 1. 项目目标 / Goal

面向桌面端与手机端的《Warhammer 40,000: Darktide》中英双语 BD 编辑器。核心目标不是复制 Games Lantern 页面，而是保留其成熟的构筑编辑信息结构，同时提供更直接的中文体验、天赋树交互、本地多套 BD 管理和静态部署能力。

A bilingual Darktide build planner for desktop and mobile, with talent-tree interaction, local multi-build management, loadout editing, and GitHub Pages deployment.

## 2. 当前已完成 / Current baseline

- 7 个职业及正式服 / `Depths of the Damned` 未来树切换。
- 可视化天赋树、连线、30 点预算、互斥节点处理。
- 桌面端悬停详情、左键选择/取消、右键取消、撤销、缩放、适配视图。
- 详情卡保持简洁：中文名、英文名、中文说明、英文说明为主。
- 多套 BD 本地保存：新建、复制、切换、删除、自动保存。
- JSON 导入 / 导出与分享链接。
- 近战 / 远程武器、祝福、祝福等级、词条、3 个珍品的配装编辑。
- 装备选择支持中英文搜索。
- 祝福按武器合法性过滤；祝福悬停 / 聚焦时显示效果说明。
- 当前职业天赋图标立即高优先级加载；其余职业图标在浏览器空闲时后台预加载。
- PWA 基础支持。
- GitHub Pages 自动部署。
- 当前 `main` 最近的 Mobile UI self-check、Talent text audit 与 Pages 部署均已通过。

## 3. 关键实现文件 / Key files

- `index.html` — 页面结构、BD 库、装备编辑弹窗。
- `styles.css` — 桌面 / 手机布局与节点、装备卡片样式。
- `app.js` — 状态、BD 库、装备编辑、祝福 Tooltip、图标包加载、交互。
- `tree-core.js` — 当前树数据。
- `tree-icons-*.js` — 按职业拆分的天赋图标包。
- `blessing-effects.js` — 祝福效果文本。
- `blessing-tier-values.js` — 祝福等级数值。
- `weapon-blessing-overrides.js` — 武器与祝福合法性覆盖。
- `.github/workflows/self-check.yml` — 手机 / 交互自检。
- `.github/workflows/text-audit.yml` — 天赋文本审计。
- `.github/workflows/pages.yml` — GitHub Pages 部署。
- `.github/workflows/refresh-trees.yml` — 天赋树刷新。

## 4. 数据与翻译原则 / Data and localization rules

1. 英文机制文本优先使用 Fatshark 官方资料、游戏数据或 Games Lantern 当前数据。
2. 天赋中文名称优先使用维护中的 Darktide 中文术语来源；避免把机器翻译当作官方译名。
3. 武器必须优先采用游戏官方简体中文译名。已有映射与规范化逻辑，但新增武器或特殊型号仍应逐项核对。
4. 祝福、词条、珍品同样需要继续核对官方简体中文；不要因为已有中文字符串就默认已经官方化。
5. 对无法可靠确认的文本，宁可保留英文或标注来源，也不要伪造“官方译名”。

## 5. 装备区 UX 原则 / Loadout UX rules

- 目标是“少点击、少层级、可搜索、能一眼看懂当前装备”。
- 武器、祝福、词条、珍品应尽量使用卡片式摘要 + 单一编辑入口，不要拆成大量难以理解的小表单。
- 祝福列表必须基于当前武器过滤。
- 祝福效果应可在不选中的情况下预览（鼠标悬停 / 键盘聚焦）。
- 默认祝福等级为 IV，但允许切换 I–IV。
- 桌面和手机都必须可用；任何重构都要继续跑现有 self-check。

Games Lantern 可作为信息结构与交互参考，但不要复制其专有代码、Logo 或商业页面。

## 6. 图标加载策略 / Icon loading

当前实现不是“只有点进职业才开始加载”：

- 当前职业：`queueCurrentIconPack()` -> 立即高优先级加载。
- 其他职业：`scheduleRemainingIconPacks()` -> 浏览器空闲时依次低优先级预加载。
- 开启 Data Saver 或极慢网络时不会强制后台预加载。

不要重新合并成一个超大的 `tree-icons.js` 首屏同步加载，否则会显著增加首次加载负担。

## 7. 下一阶段优先级 / Next priorities

### P0 — 2026-09-29 更新后的最终数据核对
`Depths of the Damned` 正式上线后，逐职业核对：
- 节点位置与连线；
- 节点名称；
- 数值与描述；
- 四个基础职业的最终树是否与预览发生变化。

### P1 — 官方简中翻译审计
重点检查：
- 武器完整型号名；
- 祝福；
- 武器词条；
- 珍品名称、主属性和词条。

必须区分“官方简中”“社区翻译”“人工补译”。

### P1 — 装备编辑可用性
继续以真实使用路径测试：
- 从空白 BD 到完整近战 + 远程 + 3 珍品需要多少点击；
- 搜索是否同时匹配中文与英文；
- 选择武器后祝福是否合法、是否立即刷新；
- 清空 / 更换装备后是否残留旧祝福；
- 手机端弹窗高度、滚动、搜索框与按钮是否顺手。

### P2 — 文档与回归
- 每次数据刷新后跑 text audit。
- 每次 UI 改动后跑 Mobile UI self-check。
- 保持 README 与本交接文件同步。

## 8. 不要回退的已定交互 / Do not regress

- 未点亮节点也可以查看详情。
- 详情弹层不堆放来源 / 调试状态等杂项。
- 中文描述保持正常段落，不要机械逐句拆行。
- 支持点击空白关闭详情。
- 桌面端保留悬停查看、右键取消、撤销、缩放。
- 手机端避免拖动时误触节点。
- 多套 BD 不能退回成只能保存一套。

## 9. 当前部署 / Deployment

静态站点通过 GitHub Actions 的 `pages.yml` 从 `main` 自动部署到 GitHub Pages。

预期站点：
`https://a1615439938-collab.github.io/Darktide-BD/`


## 10. DepthsPreview 本地试玩 Mod / Local preview mod

开发分支：`depths-preview-mod`

新增目录：`game-mod/DepthsPreview/`

目标：将网站的 `Depths of the Damned` 未来树 BD 导出为 `DTP1` 紧凑代码，
在 SoloPlay / Realms 本地主机里临时应用，不写入官方后端角色天赋。

当前 Alpha 已完成：
- 网站生成 `DTP1:20260929a:<class>:<indexes>`；
- `/depths_import`、`/depths_apply`、`/depths_status`、`/depths_off`；
- 仅允许 singleplay / player-host 且本机是 game server 时应用；
- 自动从 `tree-core.js` 生成运行时数据；
- 只有“未来树与正式服描述/高级描述/类别完全一致”的节点标为 `reuse`；
- 改动/新增节点统一标为 `custom`，必须后续显式实现，不允许静默套用旧机制。

当前未来树节点分类：
- Veteran：69 reuse / 8 custom（77）
- Zealot：60 reuse / 23 custom（83）
- Psyker：72 reuse / 10 custom（82）
- Ogryn：78 reuse / 9 custom（87）

注意：这里的 custom 数量包含“改动的旧节点 + 新节点”，不是只统计全新名称。
远程 Realms 客户端的独立构筑同步尚未完成；当前第一目标是本地主机实际试玩。
