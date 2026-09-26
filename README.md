# Darktide 中文 / English BD Planner

面向桌面端与手机端的《Warhammer 40,000: Darktide》中英双语 BD 编辑器。

## 功能 / Features
- 中文 + English 对照
- 7 个职业切换
- 正式服 / `Depths of the Damned` 未来树切换
- 可视化天赋树、连线、30 点计数与互斥节点处理
- 桌面端悬停详情、左键选择/取消、右键取消、撤销、缩放与适配视图
- 多套 BD 本地保存：新建、复制、切换、删除、自动保存
- 武器、祝福、祝福等级、词条与 3 个珍品编辑
- 装备中英文搜索
- 祝福按当前武器过滤，并支持悬停 / 聚焦预览效果
- JSON 导入 / 导出与分享链接
- 手机端适配
- PWA 基础支持

## 数据说明
当前页面用于 2026-09-29 `Depths of the Damned` 更新前后的构筑规划。

四个基础职业的未来树来自预览期数据。正式更新上线后仍需逐职业再次核对最终节点位置、连线、名称、数值与描述，不能把预览数据直接视作最终正式服数据。

## 图标加载
天赋图标按职业拆包：
- 当前职业立即高优先级加载；
- 其余职业在浏览器空闲时后台预加载；
- Data Saver / 极慢网络下避免强制后台预加载。

这样可避免首屏一次性同步加载全部大型图标资源。

## 部署
静态网站，使用 GitHub Actions 从 `main` 自动部署到 GitHub Pages。

站点：
`https://a1615439938-collab.github.io/Darktide-BD/`

## 质量检查
仓库包含：
- `Mobile UI self-check`
- `Talent text audit`
- GitHub Pages 部署工作流
- 未来树刷新工作流

UI 或数据改动后应继续保持相应检查通过。

## 翻译原则
- 武器优先使用游戏官方简体中文译名；
- 祝福、词条、珍品同样应持续核对官方简中；
- 天赋名称与说明需区分官方资料、社区维护翻译和人工补译；
- 无法可靠确认时，不把机器翻译或临时译法冒充官方译名。

## 项目交接
当前实现状态、关键文件、不要回退的交互和下一阶段优先级见 [HANDOFF.md](./HANDOFF.md)。

## 实现来源与归因 / Implementation attribution

本项目的交互式天赋树实现参考了 [LawsonMode/darktide-tree-planner](https://github.com/LawsonMode/darktide-tree-planner)。该项目 README 明确说明其原创编辑器代码可自由使用与修改。

- 天赋树布局、连线与效果文本：Games Lantern、Fatshark 官方资料与维护中的游戏数据来源
- 游戏内天赋图标：其版权归对应游戏权利人所有，仅用于识别天赋
- 中文名称：优先采用维护中的 Darktide 中文术语来源，并继续核对官方简中
- 本项目不会复制 Games Lantern 的专有源代码、Logo 或广告 / 商业页面；仅复现 BD 编辑器所需的公开交互与信息结构
