---
name: weekly-cross-platform-sync
description: 管理 B 站、微博、知乎和小黑盒之间的周报同步工作流，尤其适用于同一份图文周报需要跨多个平台发布、复用素材并核对账号和结果的场景。
---

# 跨平台周报同步总工作流

本 skill 负责编排，不替代平台 skill。它把来源采集、目标发布和验证拆开，避免把某个平台的选择器、Cookie 逻辑或账号假设复制到其他平台。

## 路由

| 来源 | 目标 | 使用的 skill |
| --- | --- | --- |
| B 站文集 | 小黑盒 | [bilibili-xiaoheihe-weekly](../bilibili-xiaoheihe-weekly/SKILL.md) |
| 微博动态/周报 | 小黑盒或其他目标 | [weibo-weekly-sync](../weibo-weekly-sync/SKILL.md) + 对应目标 skill |
| B 站或微博素材 | 知乎文章 | [zhihu-weekly-sync](../zhihu-weekly-sync/SKILL.md) |
| 知乎文章 | 其他目标 | [zhihu-weekly-sync](../zhihu-weekly-sync/SKILL.md) 先做能力检查；必要时要求 URL/正文或另接读取适配器 |

已验证的写入适配器：

| 目标 | 默认适配器 | 重要边界 |
| --- | --- | --- |
| 微博头条文章 | [XinAloha/skills](https://github.com/XinAloha/skills/tree/main/content/post-to-weibo) | Markdown 可填充正文和本地图片；需独立 Chrome profile，组合完成后再核对并点击“发布” |
| 知乎文章 | [guoxiaoyi/liduma-article-publisher](https://github.com/guoxiaoyi/liduma-article-publisher) | 仅允许连接用户已启动的隔离浏览器会话；含图周报必须导入带嵌图的 DOCX，发布后核对公开文章正文图片数量，不得自动启动/重置浏览器 |

## 执行顺序

1. 解析用户指定的来源、目标平台、目标账号、社区/话题、是否允许直接发布，以及时间范围。
2. 读取对应平台 skill 的安装和登录前置。缺 MCP、Cookie 未加载、登录页仍可见、账号不明或 profile 被占用时停在准备阶段；不把文件名或用户口头“已登录”当作账号证明。任何平台都不得自动启动、重启、接管、关闭或重置用户的浏览器/profile。
3. 调用来源 skill **只生成一次**仓库外的统一素材清单。清单至少包含 `source`、`source_id`、`canonical_url`、`title`、`blocks`、`images`、`author` 和 `published_at`；所有目标平台都从这份清单派生，不重新抓取来源。
4. 为每个目标生成独立 payload，但保留同一 `source_id` 和素材版本。标题截断必须记录在 payload/回执中；含图知乎周报不得接受正文纯文本化或图片减少作为静默降级，遇到平台限制时停在发布前。
5. 预览并核对：正文是否完整、图片顺序是否一致、标题是否符合目标限制、来源署名是否保留、目标账号和社区/专栏是否正确。
6. 用 `source + source_id + target_account + target_scope`，必要时加正文/图片指纹去重。已有回执、草稿或目标端同源文章时先回读验证，不重复发布。
7. 按平台顺序发布，不并发重复点击。发布响应、管理列表或目标公开页面三者至少形成一条证据链；超时或结果未知时先查询，不直接重试。
8. 将最小回执保存到仓库外，报告来源、目标、账号、链接、正文/图片核验和是否需要人工审核。不要保存 Cookie、PAT、验证码、HAR 或完整原文资产到团队仓库。

## 统一素材与复用契约

一次来源采集应产生不可变的 `manifest.json`、`preview.md` 和图片目录。目标端只允许做平台适配，不得再次访问 B 站/微博抓取同一周报。

- 图片以 manifest 顺序为准，使用本地路径和来源 URL 双记录；上传失败只重试失败图片。
- 微博头条文章可以复用 Markdown 和全部本地图片；知乎含图文章必须复用同一 manifest 生成嵌图 DOCX，并在编辑器和公开页核对图片数量。知乎封面最多单独指定一张，封面缺失不能冒充正文图片已上传。
- 一个平台成功、另一个失败时，只处理失败平台；不删除或重复发布已成功平台。

## 账号切换规则

账号是每次任务的显式输入。小黑盒通过 `XIAOHEIHE_COOKIE_PATH` 选择 Cookie；微博发布适配器使用独立 `~/.config/baoyu-skills/chrome-profile`；知乎发布适配器使用 `LIDUMA_AGENT_BROWSER_PROFILE` 指向的独立 profile。切换账号后的登录、关闭专用窗口和 profile 解锁都由用户手动完成；skill 只做只读核对。profile 被占用、路径不明确或疑似普通 Chrome profile 时立即停止，不能自动处理。

## 安装总览

- 小黑盒：安装 [GalgameCriticism/XiaoheiheMcpServer](https://github.com/GalgameCriticism/XiaoheiheMcpServer) 并构建 `XiaoheiheMcpServer.Stdio`。
- 微博来源读取：`uv tool install mcp-server-weibo`，配置 `uvx --from mcp-server-weibo mcp-server-weibo`；该项目不是微博写入器。
- 微博发布：安装 [XinAloha/skills](https://github.com/XinAloha/skills) 中的 `content/post-to-weibo/scripts`，执行 `npm install`，运行时使用 `npx -y bun weibo-article.ts <preview.md> --profile <private-profile>`。
- 知乎发布：安装 [guoxiaoyi/liduma-article-publisher](https://github.com/guoxiaoyi/liduma-article-publisher) 与 `agent-browser`，用已有 manifest 生成临时 DOCX/封面目录；只有适配器支持连接用户已启动的隔离会话时才执行检查和发布，否则停下，不自动启动浏览器。发布后回读公开页。此前的 [yangming0506/zhihu-auto-publish](https://github.com/yangming0506/zhihu-auto-publish) 仅作为备用探索适配器，若它重定向登录页或只打印“完成”而没有公开 URL，立即判失败，不重置或切换用户浏览器。

旧的 [Victorzwx/zh_mcp_server](https://github.com/Victorzwx/zh_mcp_server) 保留为兼容/探索方案；它的 Cookie 文件和 Selenium 流程不自动复用上述 Playwright profile。

各平台具体工具名、选择器和能力限制以独立 skill 及上游版本为准；总工作流只维护路由和共同验收规则。
