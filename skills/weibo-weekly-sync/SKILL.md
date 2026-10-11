---
name: weibo-weekly-sync
description: 使用微博读取适配器或用户提供的授权素材处理周报，并在要求微博头条文章、微博跨平台同步或微博图文发布时使用。
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

## 微博写入适配器

`qinyuanpei/mcp-server-weibo` 当前是读取适配器，不能冒充微博发布器。需要写入微博时使用已验证的 [XinAloha/skills](https://github.com/XinAloha/skills/tree/main/content/post-to-weibo)：

```bash
git clone https://github.com/XinAloha/skills.git <private-workdir>/xinaloha-skills
cd <private-workdir>/xinaloha-skills/content/post-to-weibo/scripts
npm install --no-audit --no-fund
npx -y bun weibo-article.ts <private-material-dir>/preview.md \
  --profile <private-profile>/baoyu-skills/chrome-profile
```

首次使用由用户在独立 profile 中手动登录微博；如果该 profile 被手动 Chrome 占用，skill 必须停下并提示用户自行关闭或解锁，不能自动启动、接管、关闭、重启或杀掉任何 Chrome，也不能使用普通 Chrome profile。脚本会填充头条文章，不会把“保存草稿”当作发布。

发布前必须验证：标题不超过 32 字、导语不超过 44 字、正文图片数与 manifest 一致、没有 `WBIMGPH_` 占位符、页面显示目标昵称。用户已授权直接发布时，再点击编辑器中精确匹配的“发布”按钮，禁止点击“保存草稿”；捕获 `draft/publish` 响应并核对成功码后，访问返回的 `https://weibo.com/ttarticle/p/show?id=...` 公开地址验证标题和正文。

适配器应按 manifest 中的图片清单处理多图；页面会把 ProseMirror 分隔图也计入普通 `img` 数量，验证应统计 `.image-view__body__image` 和占位符，不要仅看 `img` 总数。若平台必须改用普通微博，使用 [CoPaw weibo_publish](https://github.com/reboasda-ship-it/copaw_skills/tree/main/weibo_publish) 时遵守其每条最多 9 张图、2000 字和默认 5 分钟间隔，并将拆分结果记录为独立 payload。

## 去重与核验

使用 `source=weibo`、来源账号 ID、微博内容 ID、目标账号和目标社区组成去重键。重复运行先检查仓库外回执和目标平台已有内容；回执存在时回读验证，不盲目重发。最终报告来源链接、选中的内容 ID、素材完整性、目标账号/社区、发布链接和核验状态。

## 能力边界

当前上游项目提供微博读取能力，不保证具备发布、编辑或删除微博的工具。因此“同步到微博”若要求写入微博，必须另行提供经授权的微博发布适配器；本 skill 不能把读取工具冒充发布工具。

跨平台任务中，微博只消费 `weekly-cross-platform-sync` 生成的一份 manifest；已成功的其他平台不触发微博重新抓取。发布超时或结果未知时先按来源 ID、目标账号和标题回读，不直接重跑脚本。
