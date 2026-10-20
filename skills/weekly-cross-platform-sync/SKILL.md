---
name: weekly-cross-platform-sync
description: 管理 B 站、微博、知乎和小黑盒之间的周报同步工作流，尤其适用于同一份图文周报需要跨多个平台发布、复用素材并核对账号和结果的场景。
---

# 跨平台周报同步总工作流

本 skill 负责编排，不替代平台 skill。它把来源采集、目标发布和验证拆开，避免把某个平台的选择器、Cookie 逻辑或账号假设复制到其他平台。

## 路由

| 来源 | 目标 | 使用的 skill |
| --- | --- | --- |
| B 站文集 | 小黑盒 | [xiaoheihe-weekly-sync](../xiaoheihe-weekly-sync/SKILL.md) |
| 微博动态/周报 | 小黑盒或其他目标 | [weibo-weekly-sync](../weibo-weekly-sync/SKILL.md) + 对应目标 skill |
| B 站或微博素材 | 知乎文章 | [zhihu-weekly-sync](../zhihu-weekly-sync/SKILL.md) |
| 知乎文章 | 其他目标 | [zhihu-weekly-sync](../zhihu-weekly-sync/SKILL.md) 先做能力检查；必要时要求 URL/正文或另接读取适配器 |

已验证的写入适配器：

| 目标 | 默认适配器 | 重要边界 |
| --- | --- | --- |
| 微博头条文章 | 本仓库 `skills/weibo-weekly-sync/scripts/weibo-compose.cjs`（编排思路来自 [XinAloha/skills](https://github.com/XinAloha/skills/tree/main/content/post-to-weibo)） | 直排 v5 编辑器：标题/导语/正文/逐图粘贴；上游 `weibo-article.ts` 的 Chrome 启动器不带 `--no-sandbox`，在本机会以 `CDP connection closed` 失败，不要直接用它启动浏览器 |
| 知乎文章 | 本仓库 `skills/zhihu-weekly-sync/scripts/zhihu-compose.cjs` | 直排正文（DOCX 导入当前被直答知识库配额拦截）；图片按 `/v2-<32hex>` 判定完成，禁止重复上传重试 |

两个平台的脚本共用同一套会话约定：`scripts/browser-session.cjs` 的 `attach()` 复用已在运行的专用 Chrome，一步结束不关窗口，下一步继续复用（详见 [浏览器会话规则](references/browser-session.md)）。

## 执行顺序

1. 解析用户指定的来源、目标平台、目标账号、社区/话题、是否允许直接发布，以及时间范围。
2. 读取对应平台 skill 的安装和登录前置，只检查所选适配器实际需要的依赖：MCP 模式检查服务及其 Cookie，浏览器模式检查连接工具、会话和真实账号。必需依赖缺失、登录页仍可见或账号不明时停在准备阶段；不把文件名或用户口头“已登录”当作账号证明。连接、启动与断线恢复遵守 [浏览器会话规则](references/browser-session.md)：用户已明确允许自动启动时，可以启动同一独立 profile，始终不得重置浏览器。
3. 精确选择用户指定的期号；未指定时才取最新一期。指定期号不在文集里时定位其原文 URL，核对作者和期号，不能用最新一期替代。调用来源 skill **只生成一次**仓库外的不可变素材清单及 SHA-256。清单至少包含 `source`、`source_id`、`canonical_url`、`title`、`blocks`、`images`、`author` 和 `published_at`；所有目标平台从这份清单派生，不重新抓取来源。
4. 为每个目标生成独立 payload，但保留同一 `source_id` 和素材版本。标题截断必须记录在 payload/回执中；含图知乎周报不得接受正文纯文本化或图片减少作为静默降级，遇到平台限制时停在发布前。
5. 预览并核对：正文是否完整、图片顺序是否一致、标题是否符合目标限制、来源署名是否保留、目标账号和社区/专栏是否正确。
6. 用 `source + source_id + target_account + target_scope + content_type`，必要时加正文/图片指纹去重。已有回执、草稿或目标端同源文章时先回读验证，不重复发布；同一期视频不能代替文章。
7. 按平台顺序发布，不并发重复点击。发布响应、管理列表或目标公开页面三者至少形成一条证据链；超时或结果未知时先查询，不直接重试。
8. 将最小回执保存到仓库外，按下方“最终回复契约”输出每个成功平台的公开链接、正文/图片核验和其他平台状态。不要保存 Cookie、PAT、验证码、HAR 或完整原文资产到团队仓库。

## 统一素材与复用契约

一次来源采集应产生不可变的 `manifest.json`、`preview.md` 和图片目录。目标端只允许做平台适配，不得再次访问 B 站/微博抓取同一周报。

- 图片以 manifest 顺序为准，使用本地路径和来源 URL 双记录；上传失败只重试失败图片。
- 微博头条文章可以复用 Markdown 和全部本地图片；知乎含图文章必须复用同一 manifest 生成嵌图 DOCX，并在编辑器和公开页核对图片数量。知乎封面最多单独指定一张，封面缺失不能冒充正文图片已上传。
- 一个平台成功、另一个失败时，只处理失败平台；不删除或重复发布已成功平台。
- 原图过大时从原素材派生优化图片和 DOCX，记录每张图片的原序号、源 SHA-256 和平台托管 URL；不改写源 manifest。阅读 [素材压缩与续传](references/material-recovery.md)，按真实平台限制控制体积，保留全部图片及其顺序。

## 最终回复契约：成功必须附公开链接

最终回复直接列出**每个已成功平台的可点击公开文章链接**，不能只写“已发布”、只给本地回执或让用户自行查找。已有文章回读通过同样输出原公开链接；部分平台失败也先列出全部已成功链接，再说明其余平台状态。

推荐输出结构：一句结果、成功链接列表、尚未完成的平台及原因（如果存在）。例如：

```markdown
已发布并核对正文及全部配图。

- 微博：[本期文章](实际公开URL)
- 知乎：[本期文章](实际公开URL)
- 小黑盒：[本期文章](实际公开URL)
```

公开 URL 必须来自发布响应或已核实的管理记录，并完成公开页回读；草稿、编辑器、登录页和本地文件路径不能填在成功链接位置。没有公开 URL 或回读未通过的目标保持 `submitted`、`pending_review`、`unknown` 或 `failed`，不能写 `published`。回执必填项见 [manifest 与回执契约](references/manifest.md)。

## 无人值守验收

区分“本期由代理自动诊断修复后完成”与“固定脚本完整跑通”。记录初始授权后的人工作业次数、恢复步骤、各端公开页核验、是否重复提交以及是否重置 profile。一次成功不能证明跨期长期稳定；尚需代理临时改脚本时如实记录，不能宣称单命令已经稳定。

## 账号切换规则

账号是每次任务的显式输入。小黑盒通过 `XIAOHEIHE_COOKIE_PATH` 选择 Cookie；微博发布适配器使用独立 `~/.config/baoyu-skills/chrome-profile`；知乎使用 `LIDUMA_AGENT_BROWSER_PROFILE` 指向的独立 profile。登录、账号切换、关闭用户窗口和 profile 解锁由用户手动完成。已有同一独立 profile 的可用 CDP 会话可以连接；锁文件不是关闭该会话的理由。路径不明确、被其他进程占用或疑似普通 Chrome profile 时停止。

## 安装总览

- 小黑盒：安装 [GalgameCriticism/XiaoheiheMcpServer](https://github.com/GalgameCriticism/XiaoheiheMcpServer) 并构建 `XiaoheiheMcpServer.Stdio`。
- 微博来源读取：`uv tool install mcp-server-weibo`，配置 `uvx --from mcp-server-weibo mcp-server-weibo`；该项目不是微博写入器。
- 微博发布：安装 [XinAloha/skills](https://github.com/XinAloha/skills) 中的 `content/post-to-weibo/scripts`，执行 `npm install`；已授权启动独立浏览器且 profile 未被占用时可运行 `npx -y bun weibo-article.ts <preview.md> --profile <private-profile>`。有可用会话时优先连接并复用现有草稿；此脚本只填充，发布及核验仍须执行。
- 知乎发布：安装 [guoxiaoyi/liduma-article-publisher](https://github.com/guoxiaoyi/liduma-article-publisher) 与 `agent-browser`，用已有 manifest 生成临时 DOCX/封面目录；采用已经确认不会重置或切换 profile 的连接方式。已授权自动启动时可按共享会话规则启动独立浏览器，再连接导入，不能直接假设旧 CLI 支持安全连接。此前的 [yangming0506/zhihu-auto-publish](https://github.com/yangming0506/zhihu-auto-publish) 仅作为备用探索适配器，若它重定向登录页或只打印“完成”而没有公开 URL，判为未完成，不重置或切换用户浏览器。

旧的 [Victorzwx/zh_mcp_server](https://github.com/Victorzwx/zh_mcp_server) 保留为兼容/探索方案；它的 Cookie 文件和 Selenium 流程不自动复用上述 Playwright profile。

各平台具体工具名、选择器和能力限制以独立 skill 及上游版本为准；总工作流只维护路由和共同验收规则。
