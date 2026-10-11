---
name: zhihu-weekly-sync
description: 在用户要求把获授权的周报发布到知乎文章/专栏、或需要判断知乎来源读取能力时使用，尤其适用于 Playwright 持久化登录态和发布结果校验。
---

# 知乎周报同步

本 skill 是知乎发布端适配器：把经核验的周报素材发布为知乎文章。素材可以来自 B 站、微博或用户提供的知乎文章 URL；发布授权来自当前任务，目标账号必须在发布前核对。

## 默认发布适配器：Playwright 持久化 profile

跨平台周报发布默认使用 [yangming0506/zhihu-auto-publish](https://github.com/yangming0506/zhihu-auto-publish)，而不是把旧 MCP 的 Cookie 文件当作通用登录态：

```bash
git clone https://github.com/yangming0506/zhihu-auto-publish.git <private-workdir>/zhihu-auto-publish
cd <private-workdir>/zhihu-auto-publish
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm install --no-audit --no-fund
```

先在 `~/.openclaw/browser-profiles/zhihu` 手动登录，并确认能看到知乎写作页；关闭这个手动 Chrome 后再让 Playwright 接管同一 profile。登录检查必须同时满足写作页元素可见和有效 `z_c0`，仅查询到 Cookie 名称不代表登录有效；如果截图显示登录页，立即停止，不填正文、不点击发布。

统一素材清单转换为临时 JSON（至少含 `title`、`body`、`history_title`，正文末尾保留来源 URL），从已有素材直接运行：

```bash
AUTO_HOT_DEBUG=1 \
MATRIX_PUBLISH_ARTICLE_JSON=<private-material-dir>/zhihu-article.json \
MATRIX_PUBLISH_ONLY=zhihu \
PLAYWRIGHT_HEADLESS=1 \
ENABLE_BROWSER_PUBLISH=1 \
.venv/bin/python main.py
```

不要在搬运周报时启用热点抓取、DeepSeek 成文或重新访问 B 站；`AUTO_HOT_DEBUG=1` 在这里的作用是允许加载已有 JSON。脚本会填充正文、点击发布并检查成功提示/`zhuanlan.zhihu.com/p/` URL。结果未知时先查作者文章列表或公开 URL，不要直接重试。

当前适配器默认 `skip_cover: true`，适合周报正文版；知乎端最多单独指定一张封面，不能声称 40 张微博/B站配图已经全部上传。平台格式适配造成的图片省略必须写入回执。

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
2. 先用与发布器相同的持久化 profile 确认当前登录账号，再调用发布器。不要用 Cookie 文件名、profile 名或用户口头描述推断账号。
3. 如使用旧 MCP，工具名沿用项目当前的拼写 `create_atticle`，参数为 `title`、`content`、可选 `images` 和 `topic`；它的 Cookie 文件与 Playwright profile 不互通。
4. 由于当前发布适配器不保证正文全量配图，先按目标格式整理；不能声称所有原图都已作为知乎正文图片上传。若素材要求保留全量图片，先报告能力限制并等待目标格式确认。
5. 发布后回读知乎文章 URL、标题、作者和封面；无法取得公开 URL、页面仍为登录页或账号不匹配时，不把提交响应单独当作成功。

## 能力边界

`zh_mcp_server` 当前是知乎自动发文章服务，不提供可靠的“读取某账号最新文章/周报列表”工具。因此“从知乎搬运最新一期”必须由用户提供文章 URL/正文，或接入另一个经过验证的读取适配器；不能用 `create_atticle` 反推来源内容。将 B 站或微博周报同步到知乎属于本 skill 的正常用法。

## 去重与核验

以来源平台、来源内容 ID、目标知乎账号组成去重键；先查仓库外回执和目标账号文章列表，再决定发布或回读。回执记录标题、来源 URL、目标账号、文章 URL、封面状态和核验时间，不记录 Cookie 或令牌。跨平台任务只消费已有 manifest，不重新抓取来源；一端已成功时，知乎失败只重跑知乎。
