---
name: weibo-weekly-sync
description: 使用微博读取适配器或用户提供的授权素材处理周报，并在要求微博头条文章、微博跨平台同步或微博图文发布时使用。
---

# 微博周报同步

本 skill 负责微博来源读取与微博头条文章发布端适配；跨平台发布交给总工作流和其他目标 skill。默认只处理用户拥有或明确获授权的账号、关键词和内容。

## 微博作为来源时：安装读取 MCP

仅微博来源读取需要此 MCP。B站等已有 manifest 同步到微博时，直接进入“微博写入适配器”，不安装或调用读取 MCP、不重新抓取来源。

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

## 微博作为来源的工作流

1. 明确微博来源账号、文集/关键词、时间范围、目标平台、目标账号和目标社区；没有来源账号或查询条件时先停在准备阶段，不猜测来源。
2. 用 `search_users` 解析并核对账号，再用 `get_feeds` 获取其最新动态。需要按关键词找文章时使用 `search_content`，必要时用 `get_comments`、`search_topics` 补齐上下文。
3. 用户指定期号时精确定位该期，未指定时依据微博内容 ID 和发布时间选最新；不要把置顶、转发或纯广告误当周报。记录来源账号、内容 ID、发布时间和原始链接。
4. 将正文、段落顺序、图片 URL/本地临时文件和署名写入仓库外的统一素材清单。图片按原顺序核对；抓取失败、权限限制或正文不完整时只输出准备失败，不发布残稿。
5. 交给 `weekly-cross-platform-sync` 按目标平台执行预览、账号核对、发布和回读验证。目标为小黑盒时复用 [xiaoheihe-weekly-sync](../xiaoheihe-weekly-sync/SKILL.md) 中的目标端发布流程；不要在本 skill 复制小黑盒选择器。

## 微博写入适配器

`qinyuanpei/mcp-server-weibo` 当前是读取适配器，不能冒充微博发布器。

### 一个窗口贯穿全流程（不要反复重启浏览器）

`scripts/browser-session.cjs` 的 `attach(profileDir, port)` 先 `connectOverCDP` 连接已在运行的专用 Chrome，只有探测不到调试端口时才启动一次（`--no-sandbox --remote-debugging-port=<port>`，detached）。微博默认端口 `9333`（`CHROME_DEBUG_PORT` 可覆盖），与知乎的 `9444` 分开。每步结束都不关窗口，下一步重新 `attach`。

### 不要用上游适配器自带的启动器

`XinAloha/skills` 的 `weibo-article.ts` 内容编排可参考，但它通过 `baoyu-chrome-cdp` 启动 Chrome 时**不带 `--no-sandbox`**，在受限环境下 Chrome 直接退出，表现为 `Error: CDP connection closed.`。改用 `scripts/weibo-compose.cjs`（Playwright 直排），只保留“标题/导语/正文/图片”的编排思路。

### 编辑器结构与直排做法（v5，tiptap/ProseMirror）

- 入口 `https://card.weibo.com/article/v3/editor`，已有草稿时 URL 形如 `#/draft/<id>`；有“写文章”按钮就先点它。
- 身份核对：编辑器壳层会渲染登录账号昵称，必须等于 `Galgame批评`。**不要**用 `weibo.com` 首页判断登录态：未登录也会先渲染首页再跳 `newlogin`，DOM 不可靠。
- 标题是 `textarea[placeholder*="请输入标题"]`（**不是 input**，32 字上限），导语是 `textarea[placeholder*="导语"]`（44 字上限）。
- 正文：向 `.ProseMirror` 派发带 `text/html` 的 `ClipboardEvent('paste')`，图片位置先写成 `WBIMGPH_<n>` 文本占位。
- 图片必须“真实选区 + 合成粘贴”：先按占位文本的 `Range` 矩形做**真实鼠标点击**，用 `Shift+ArrowRight` 选中整个 token，按 `Backspace` 删除，再派发携带 `File` 的 `ClipboardEvent('paste')`。
  - 只派发 paste 不选 token：图片会被插到文末，token 文本残留。
  - 用 `execCommand('delete')` 删 token：ProseMirror 不认这个选区，粘贴仍落在旧位置。
  - 滚动会改变布局，token 矩形要取两次（滚动后重算），并在删除前校验 `window.getSelection()` 是否等于 token。
- 上传中状态是 `figure.wb-node-image` 内的 `image-view__body--uploading`，完成后 `figure img` 的 `src` 变为 `https://wx*.sinaimg.cn/...`；`r.sinaimg.cn/images/tc2.service.jpg` 是编辑器占位图，不能算成功。
- 校验：`figure` 数 = manifest 图片数；所有 `src` 为 `http(s)` 且不是 `tc2.service`；正文无 `WBIMGPH_` 残留；归一化全文与 manifest 一致。

### 发布步骤（v5 单页 + 弹窗）

1. 底部是“保存草稿 / 预览 / 下一步”。用**真实 locator 点击** `button:has-text("下一步")`；用 DOM `click()` 点不动它。
2. 点完后出现发布确认弹窗（内容形如 `字数 | 公开 | 发布`），页面同时多出一个“发布”按钮。
3. 弹窗遮罩 `.n-modal-mask` 会拦截 footer 的“发布”按钮，此时用 DOM `click()` 触发 `button` 文本为“发布”的最后一个元素；不要用 `force: true` 反复重试。
4. 成功后 SPA 跳到 `#/history/<draftId>`——**这不是公开链接**，草稿箱也会被清空。
5. 公开链接从移动端时间线接口取：`https://m.weibo.cn/api/container/getIndex?type=uid&value=<uid>&containerid=107603<uid>`，找最新一条“发布了头条文章”的 `page_info.page_url`，形如 `https://weibo.com/ttarticle/p/show?id=230940...`。
6. 回读公开页核对标题、作者（`Galgame批评`）、图片数（应等于 manifest 图片数）和正文长度，写入回执后才算成功。

### 登录态失效时

Cookie 丢失时编辑器与首页都会 302 到 `newlogin`。用 `scripts/weibo-login.cjs` 复用同一个窗口停在登录页等用户扫码（默认 10 分钟，`WEIBO_LOGIN_WAIT_MIN` 可调），扫码完成后脚本只输出昵称、不关窗口。绝不为“重置登录态”删除 profile 或 `Singleton*` 文件——那会直接清掉已登录 Cookie，必须让用户重新扫码。


## 去重与核验

使用实际来源平台、来源账号 ID、来源内容 ID、目标账号和目标范围组成去重键；B站素材同步到微博时来源仍是 B站。重复运行先检查仓库外回执和目标平台已有内容；回执存在时回读验证，不盲目重发。最终报告素材完整性、目标账号/范围和核验状态，并必须直接给出可点击的微博公开文章链接；不能用草稿或本地回执链接替代。

## 能力边界

当前上游项目提供微博读取能力，不保证具备发布、编辑或删除微博的工具。因此“同步到微博”若要求写入微博，必须另行提供经授权的微博发布适配器；本 skill 不能把读取工具冒充发布工具。

跨平台任务中，微博只消费 `weekly-cross-platform-sync` 生成的一份 manifest；已成功的其他平台不触发微博重新抓取。发布超时或结果未知时先按来源 ID、目标账号和标题回读，不直接重跑脚本。
