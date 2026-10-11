---
name: bilibili-xiaoheihe-weekly
description: 将用户拥有或获授权的 B 站文集最新图文周报同步到指定小黑盒账号和社区，保留正文、图片顺序和来源，并验证发布结果。用户要求搬运周报、B站同步小黑盒或发布 Gal 周报时使用。
---

# B 站周报同步小黑盒

从用户指定的文集确定最新一期，保持原文和配图，使用用户指定的小黑盒账号在指定社区发布一次。发布授权来自当前任务；已有明确授权时继续执行，无须再次要求确认。

## 前置依赖：安装小黑盒 MCP

小黑盒是本工作流的目标发布端。使用团队维护的 MCP 服务：
<https://github.com/GalgameCriticism/XiaoheiheMcpServer>

首次使用时：

```bash
git clone https://github.com/GalgameCriticism/XiaoheiheMcpServer.git
cd XiaoheiheMcpServer
dotnet build src/XiaoheiheMcpServer.Stdio/XiaoheiheMcpServer.Stdio.csproj -c Release
```

将构建后的 `XiaoheiheMcpServer.Stdio.dll` 配置为 MCP 的 stdio 服务，并按实际环境设置：

```toml
[mcp_servers.xiaoheihe]
type = "stdio"
command = "dotnet"
args = ["/absolute/path/to/XiaoheiheMcpServer.Stdio.dll"]

[mcp_servers.xiaoheihe.env]
XIAOHEIHE_CHROMIUM_PATH = "/absolute/path/to/Chrome"
XIAOHEIHE_COOKIE_PATH = "/private/path/to/account-cookie.json"
```

Cookie 文件只保存在本机并限制权限；更换账号或 `XIAOHEIHE_COOKIE_PATH` 后，必须重启 MCP 进程，让浏览器上下文重新加载 Cookie。发布前调用 `check_login_status`，以返回的用户名确认账号，不要仅凭 Cookie 文件名判断账号。

## 运行输入

从用户任务和本地配置取得文集 URL、目标账号名称、目标社区（Gal 周报通常为 `Gal游戏综合区`）。Cookie 通过 `XIAOHEIHE_COOKIE_PATH` 引用本机文件，浏览器可执行文件通过 `XIAOHEIHE_CHROMIUM_PATH` 指定。不要从某个文件名推断已登录的账号。

团队仓库不保存 Cookie、PAT、用户绝对路径、HAR、原文图片或运行回执。Cookie 在执行进程内读取，不作为命令行参数或日志内容输出。MCP 和浏览器自动化可按环境择优；浏览器辅助脚本依赖 Node.js、`playwright` 或 `playwright-core` 及可用的 Chromium。源码抓取脚本仅依赖 Python 3 标准库。

## 源稿准备

运行 `scripts/fetch_weekly.py <文集URL> --output <仓库外工作目录> [--title <不超过30字的标题>]`。

脚本读取 B 站文集列表，核对返回数量和作者，按 `publish_time`、文章 ID 确定最新一期；新版专栏使用 `dyn_id_str` 对应的 `/opus/<id>` 页，从 `window.__INITIAL_STATE__` 的 `MODULE_TYPE_CONTENT` 取完整段落。不能把动态摘要当作完整原文。

输出 `manifest.json`、`preview.md` 和图片文件。检查标题、期号、作者、正文和图片数量。标题超过小黑盒 30 字限制时，仅缩短标题，完整原标题保留在正文开头；保留来源链接及原有署名。图片包括原始封面和正文配图，按顺序插入。脚本遇到不支持的段落类型、旧版专栏或不完整列表会退出；根据页面实际结构补齐提取方式后再发布。

## 账号和发布

阅读 [references/heybox-editor.md](references/heybox-editor.md) 后使用 `scripts/publish_weekly.cjs`，或在可用浏览器会话中执行相同流程。准备模式在编辑器中核对账号、正文、图片和社区，并保存可重建的本地内容；用户任务已经授权发布时可以直接使用 `--publish` 执行完整流程。已有发布回执时使用 `--verify` 回读核验。

目标账号以文章预览作者或个人主页返回值为准。旧版 MCP 的 `check_login_status` 只检查已经下线的 `p.user-box__username`，可能把实际已登录误报为未登录。使用上述仓库最新版本后，命令会兼容当前顶部导航、用户页和文章作者区域；作者预览显示指定账号且编辑器可用时，以实际页面为准。作者不匹配则停止发布，报告所需登录切换。

小黑盒长周报使用“发布文章”编辑器。批量上传图片后，将正文和已上传图片依原始顺序粘贴为富文本。发布前核对全文、全部图片、精确匹配的社区名称，以及账号身份。仅点击发布按钮不能视为成功，必须查看发布响应和管理列表/帖子详情，取得帖子链接并核对作者和社区。

以 `source_author_id + article_id` 作为本地去重键，并保存发布回执到仓库外工作目录。重复运行时先查回执和账号管理页；发现同一期帖子则回读验证，避免再次发布。提交后超时或结果不明时先查管理页与帖子，不能盲目重试发布。

## 交付

报告源稿期号、B 站来源、小黑盒帖子链接、账号、社区和图文核验结果。需要登录、审核或人工处理时明确区分“准备完成”“提交待审核”“已公开发布”。团队 skill 的更新仅包含可复用操作和已验证的结构变化，不包含本次账号私密信息或源稿资产。
