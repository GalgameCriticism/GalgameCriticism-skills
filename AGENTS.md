# AGENTS.md

本文件是仓库级 agent 规则，对本仓库内的一切改动生效。开始工作前先读完本文件。

## 仓库定位

GalgameCriticism 团队共用的 Agent Skills 仓库，会容纳各种各样的 skill。仓库级文件（根 README、本文件）只做仓库级的事；具体业务内容一律放在对应 skill 目录内。

## 根 README 规则（强制）

1. **不放具体 skill 的介绍**：根 README 的「技能目录」只列 skill 名字与链接（指向该 skill 的 `README.md`），不写用途描述、工作流或业务流程。
2. **具体内容下沉**：某 skill 的用途介绍、工作流、流程图等，放到 `skills/<name>/README.md`（面向人，讲「这是什么」）；agent 的执行说明与 frontmatter 仍在 `skills/<name>/SKILL.md`（面向 agent，讲「怎么执行」）。
3. **目录同步**：每次新增、重命名或删除 skill，提交前必须同步更新根 README 的技能目录，使目录与 `ls skills/` 一致；新 skill 必须自带 `README.md`（至少一句定位 + 指向 SKILL.md）。

## 提交前自检

- 根 README 技能目录与 `skills/` 实际目录一致（不多、不少、名字相同）；
- 根 README 中没有具体 skill 的介绍、业务流程或平台细节；
- 新 skill 自带 `README.md`，且 `SKILL.md` frontmatter 的 `name` / `description` 正确；
- 未提交任何成员的用户名路径、令牌、Cookie、浏览器配置目录或运行产物——提交前对新增文件做凭证与个人路径脱敏扫描。

## 发布与浏览器约定（跨 skill 生效）

- 工作流里涉及发布时，以用户授权的来源、账号和目标范围为准；说明发布前验证、结果核验和重复发布的处理方式。
- 发布完成后的最终回复必须直接提供每个成功平台的可点击公开文章链接；部分失败时也列出已成功链接及其余平台状态。
- 浏览器优先连接独立会话；用户明确授权自动启动时可启动同一专用 profile，始终不重置或清理登录态。
- 账号信息、Cookie 文件、下载的原文与运行记录保留在使用者本机，运行时传入，不入仓库。
