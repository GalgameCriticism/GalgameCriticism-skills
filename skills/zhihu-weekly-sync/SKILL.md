---
name: zhihu-weekly-sync
description: 在用户要求把获授权的周报发布到知乎文章/专栏、或需要判断知乎来源读取能力时使用，尤其适用于 agent-browser 持久化登录态、正文导入和公开页结果校验。
---

# 知乎周报同步

本 skill 是知乎发布端适配器：把经核验的周报素材发布为知乎文章。素材可以来自 B 站、微博或用户提供的知乎文章 URL；发布授权来自当前任务，目标账号必须在发布前核对。

## 默认发布适配器：agent-browser 持久化 profile

跨平台周报发布默认使用已跑通的 [guoxiaoyi/liduma-article-publisher](https://github.com/guoxiaoyi/liduma-article-publisher)，而不是把旧 MCP 的 Cookie 文件当作通用登录态：

```bash
git clone https://github.com/guoxiaoyi/liduma-article-publisher.git <private-workdir>/liduma-article-publisher
cd <private-workdir>/liduma-article-publisher
npm install --no-audit --no-fund
npm install agent-browser --no-audit --no-fund
npx agent-browser install
```

使用独立 profile 登录并检查写作页：

```bash
LIDUMA_AGENT_BROWSER_PROFILE=<private-profile>/openclaw/browser-profiles/zhihu \
AGENT_BROWSER_HEADED=false \
npx tsx src/cli.ts --check-login --platform=zhihu
```

如果未登录，适配器会自动以有头模式打开登录页；完成登录后再次确认写作页和目标账号。不要把 cookie 文件名、`z_c0` 名称或用户口头“已登录”当作账号证明。

统一素材清单转换为临时文章目录：目录至少包含以完整标题命名的 `.docx`、`cover.png` 和 `index.md`。正文 DOCX 必须从已有 manifest 的 paragraph/image 顺序生成，并把图片作为真正的嵌入对象写入 DOCX；不能用 `textutil` 把 Markdown 直接转成“看起来像文章”的纯文本 DOCX。封面最多使用 manifest 中一张图片；不要为知乎重新抓取 B 站。

从已有素材直接发布：

```bash
LIDUMA_AGENT_BROWSER_PROFILE=<private-profile>/openclaw/browser-profiles/zhihu \
AGENT_BROWSER_HEADED=false \
npx tsx src/cli.ts --publish \
  --dir=<private-material-dir>/zhihu-article \
  --platform=zhihu
```

该项目会导入 DOCX、可选上传封面并点击发布，结果写入文章目录的 `publish-log.json`。发布命令可能在写入回执后继续监听 DOM；看到成功回执后可停止监听，但必须使用同一 agent-browser 会话打开返回的公开 URL，核对标题、作者、来源链接和正文图片。公开页回读失败时不把本地日志单独当作成功。

## 正文图片保真检查

这是硬性门槛，不满足时不能点击“发布”或“更新”：

1. 上传前检查 DOCX 压缩包内 `word/media/` 的图片数与 manifest 图片块数一致；图片过大时可以压缩，但不能删图或改变顺序。
2. 导入后等待“文档导入中”结束，再检查编辑器 `[contenteditable=true]` 内的图片元素数量和图片 URL；数量应与 manifest 一致，正文中不能残留 `![配图](...)`、`images/001.png` 等 Markdown 路径。
3. 导入超时、导入错误、图片数为 0 或仍残留 Markdown 时立即停止并报告，不得以“流程完成”或本地日志代替成功。封面上传超时只允许在正文图片已经通过检查且用户不要求封面时继续，并在回执中注明封面未设置。

## 已发布纯文本文章的纠错

如果发现本次文章已经发布但正文是 Markdown/纯文本，先打开同一文章的 `/edit` 页面，在原文章中重新导入带嵌图 DOCX，等待上述图片检查通过后点击“更新”，最后回读同一个公开 URL 验证图片数量。不要因为导入失败直接创建第二篇；只有原文章不可编辑时，才向用户说明会产生重复文章并取得确认。

## 备用适配器与切换规则

[yangming0506/zhihu-auto-publish](https://github.com/yangming0506/zhihu-auto-publish) 曾作为 Playwright 备用适配器验证过，但若访问写作页被重定向到登录页，即使本地能看到 `z_c0`，也必须停止。该项目可能在失败后打印“流程已完成”，只有公开文章 URL 和公开页回读才算成功；不要在同一 profile 上盲目重复三次。

## 兼容方案：安装知乎 MCP

使用上游项目 [Victorzwx/zh_mcp_server](https://github.com/Victorzwx/zh_mcp_server)：

```bash
git clone https://github.com/Victorzwx/zh_mcp_server.git
cd zh_mcp_server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m zh_mcp_server.__login__
```

登录脚本会打开 Chrome，并在终端等待验证码；Cookie 只放在本机。stdio 配置使用虚拟环境中的 Python：

```json
{
  "mcpServers": {
    "zh_mcp_server": {
      "command": "/absolute/path/to/zh_mcp_server/.venv/bin/python",
      "args": ["-m", "zh_mcp_server"]
    }
  }
}
```

当前上游代码实际将 `zhihu_cookies.json` 放在 Python 包目录附近；`json_path` 不能替代对实际 Cookie 文件位置的检查。登录后确认文件位于本机私有目录并限制权限，绝不将虚拟环境、Cookie 或登录输出提交到团队仓库。

## 工作流

1. 接收统一素材清单，核对标题、正文、图片顺序、署名、来源链接和目标知乎账号；标题和正文未确认时只生成预览。
2. 先用与发布器相同的 agent-browser profile 确认当前登录账号，再调用发布器。不要用 Cookie 文件名、profile 名或用户口头描述推断账号。
3. 如使用旧 MCP，工具名沿用项目当前的拼写 `create_atticle`，参数为 `title`、`content`、可选 `images` 和 `topic`；它的 Cookie 文件与 Playwright profile 不互通。
4. 若素材含图片，先完成“正文图片保真检查”；检查未通过时只修复或切换适配器，不降级成纯文本发布。
5. 发布后回读知乎文章 URL、标题、作者、正文图片数量和封面状态；无法取得公开 URL、页面仍为登录页、账号不匹配或图片缺失时，不把提交响应单独当作成功。

## 能力边界

`zh_mcp_server` 当前是知乎自动发文章服务，不提供可靠的“读取某账号最新文章/周报列表”工具。因此“从知乎搬运最新一期”必须由用户提供文章 URL/正文，或接入另一个经过验证的读取适配器；不能用 `create_atticle` 反推来源内容。将 B 站或微博周报同步到知乎属于本 skill 的正常用法。

## 去重与核验

以来源平台、来源内容 ID、目标知乎账号组成去重键；先查仓库外回执和目标账号文章列表，再决定发布或回读。回执记录标题、来源 URL、目标账号、文章 URL、封面状态和核验时间，不记录 Cookie 或令牌。跨平台任务只消费已有 manifest，不重新抓取来源；一端已成功时，知乎失败只重跑知乎。
