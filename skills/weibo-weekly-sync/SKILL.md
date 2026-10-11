---
name: weibo-weekly-sync
description: 使用 mcp-server-weibo 获取用户拥有或获授权的微博周报内容，整理为可核验的周报素材并交给指定发布端。用户要求微博周报、微博同步小黑盒或从微博搬运图文时使用。
---

# 微博周报同步

本 skill 负责微博侧的来源发现、最新一期判定、正文和图片整理；发布动作交给总工作流和指定目标平台的发布 skill。默认只处理用户拥有或明确获授权的账号、关键词和内容。

## 前置依赖：安装微博 MCP

使用上游项目 [qinyuanpei/mcp-server-weibo](https://github.com/qinyuanpei/mcp-server-weibo)：

```bash
uv tool install mcp-server-weibo
```

stdio 配置示例：

```json
{
  "mcpServers": {
    "weibo": {
      "command": "uvx",
      "args": ["--from", "mcp-server-weibo", "mcp-server-weibo"]
    }
  }
}
```

该项目当前主要是读取适配器：它通过 visitor 接口获取公开数据，不是微博发布器。需要用户会话时，按上游项目提供的 `weibo-cli login` 流程登录；Cookie/session 只由本机运行环境管理，不复制到技能仓库、命令参数或日志。

## 工作流

1. 明确微博来源账号、文集/关键词、时间范围、目标平台、目标账号和目标社区；没有来源账号或查询条件时先停在准备阶段，不猜测来源。
2. 用 `search_users` 解析并核对账号，再用 `get_feeds` 获取其最新动态。需要按关键词找文章时使用 `search_content`，必要时用 `get_comments`、`search_topics` 补齐上下文。
3. 依据微博内容 ID 和发布时间排序，选择最新一期；不要把置顶、转发或纯广告误当周报。记录来源账号、内容 ID、发布时间和原始链接。
4. 将正文、段落顺序、图片 URL/本地临时文件和署名写入仓库外的统一素材清单。图片按原顺序核对；抓取失败、权限限制或正文不完整时只输出准备失败，不发布残稿。
5. 交给 `weekly-cross-platform-sync` 按目标平台执行预览、账号核对、发布和回读验证。目标为小黑盒时复用 [bilibili-xiaoheihe-weekly](../bilibili-xiaoheihe-weekly/SKILL.md) 中的目标端发布流程；不要在本 skill 复制小黑盒选择器。

## 去重与核验

使用 `source=weibo`、来源账号 ID、微博内容 ID、目标账号和目标社区组成去重键。重复运行先检查仓库外回执和目标平台已有内容；回执存在时回读验证，不盲目重发。最终报告来源链接、选中的内容 ID、素材完整性、目标账号/社区、发布链接和核验状态。

## 能力边界

当前上游项目提供微博读取能力，不保证具备发布、编辑或删除微博的工具。因此“同步到微博”若要求写入微博，必须另行提供经授权的微博发布适配器；本 skill 不能把读取工具冒充发布工具。
