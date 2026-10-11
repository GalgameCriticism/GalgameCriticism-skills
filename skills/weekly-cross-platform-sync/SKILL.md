---
name: weekly-cross-platform-sync
description: 管理 B 站、微博、知乎和小黑盒之间的周报同步工作流，路由独立平台 skill，统一素材清单、账号核对、去重、发布授权和结果回执。用户要求跨平台周报同步或同时管理多个周报渠道时使用。
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

## 执行顺序

1. 解析用户指定的来源、目标平台、目标账号、社区/话题、是否允许直接发布，以及时间范围。
2. 读取对应平台 skill 的安装和登录前置。缺 MCP、Cookie 未加载或账号不明时停在准备阶段；不把文件名当作账号证明。
3. 调用来源 skill 生成仓库外的统一素材清单。清单至少包含 `source`、`source_id`、`canonical_url`、`title`、`blocks`、`images`、`author` 和 `published_at`。
4. 预览并核对：正文是否完整、图片顺序是否一致、标题是否符合目标限制、来源署名是否保留、目标账号和社区是否正确。
5. 用 `source + source_id + target_account + target_scope` 去重。已有回执或目标端同源文章时改为回读验证，不重复发布。
6. 在用户已授权的范围内调用目标平台 skill 发布；发布响应、管理列表或目标页面三者至少形成一条可验证证据链。
7. 将最小回执保存到仓库外，报告来源、目标、账号、链接、正文/图片核验和是否需要人工审核。不要保存 Cookie、PAT、验证码、HAR 或完整原文资产到团队仓库。

## 账号切换规则

账号是每次任务的显式输入。小黑盒通过 `XIAOHEIHE_COOKIE_PATH` 选择 Cookie，知乎通过本机登录会话选择账号，微博按上游 MCP 的 visitor/session 机制工作。切换后重启对应 MCP 进程并重新运行登录状态检查；若账号和用户要求不一致，立即停止发布。

## 安装总览

- 小黑盒：安装 [GalgameCriticism/XiaoheiheMcpServer](https://github.com/GalgameCriticism/XiaoheiheMcpServer) 并构建 `XiaoheiheMcpServer.Stdio`。
- 微博：`uv tool install mcp-server-weibo`，配置 `uvx --from mcp-server-weibo mcp-server-weibo`。
- 知乎：安装 [Victorzwx/zh_mcp_server](https://github.com/Victorzwx/zh_mcp_server) 的 Python 依赖并运行其登录脚本。

各平台具体工具名、选择器和能力限制以独立 skill 及上游版本为准；总工作流只维护路由和共同验收规则。
