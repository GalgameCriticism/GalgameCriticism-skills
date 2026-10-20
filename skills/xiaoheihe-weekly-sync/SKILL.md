---
name: xiaoheihe-weekly-sync
description: 将用户拥有或获授权的 B 站指定期号或最新图文周报同步到指定小黑盒账号和社区。用户要求搬运周报、B站同步小黑盒或发布 Gal 周报时使用。
---

# B 站周报同步小黑盒

从用户指定的文集或原文定位指定期号；未指定期号时才取最新一期。保持原文和配图，使用用户指定的小黑盒账号在指定社区发布一次。发布授权来自当前任务；已有明确授权时继续执行，无须再次要求确认。

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

### Cookie 过期与重新登录

小黑盒 Cookie 有效期很短（实测约 1–2 天），过期后编辑器仍能打开，但账号显示为空或访客，发布会在最后一步失败。判断依据是页面/接口返回的用户名，不是“编辑器可编辑”。

需要重新登录时运行：

```bash
HEYBOX_DLL=/abs/path/XiaoheiheMcpServer.Stdio.dll \
HEYBOX_COOKIE=/abs/path/account-cookie.json \
python3 scripts/heybox_login.py 240
```

脚本以 `--no-headless` 启动 MCP，弹出浏览器等待用户扫码（默认 240 秒），登录成功后 MCP 会把新 Cookie 写回同一文件，并备份旧文件为 `*.bak-before-login`。这一步必须由用户完成扫码，不能自动化；扫码前先说明目标账号（例如 `Galgame批评`），避免登进错误账号。

## 运行输入

从用户任务和本地配置取得文集 URL、目标账号名称、目标社区（Gal 周报通常为 `Gal游戏综合区`）。Cookie 通过 `XIAOHEIHE_COOKIE_PATH` 引用本机文件，浏览器可执行文件通过 `XIAOHEIHE_CHROMIUM_PATH` 指定。不要从某个文件名推断已登录的账号。

团队仓库不保存 Cookie、PAT、用户绝对路径、HAR、原文图片或运行回执。Cookie 在执行进程内读取，不作为命令行参数或日志内容输出。MCP 和浏览器自动化可按环境择优；浏览器辅助脚本依赖 Node.js、`playwright` 或 `playwright-core` 及可用的 Chromium。源码抓取脚本仅依赖 Python 3 标准库。

## 源稿准备

运行 `python3 scripts/fetch_weekly.py <文集URL> --output <仓库外工作目录> [--issue <期号>] [--article-url <原文URL>] [--title <不超过30字的标题>]`。

脚本读取 B 站文集列表，核对返回数量和作者；`--issue` 只选该期，不存在或不唯一时停止，定位原文后用 `--article-url` 补充。仅未指定期号/URL时按 `publish_time`、文章 ID 取最新。新版专栏使用 `dyn_id_str` 对应的 `/opus/<id>` 页；桌面页无完整初始化状态时可读取同一文章的 `/read/mobile/<article_id>`，仍核对作者、文章 ID 和期号。从 `window.__INITIAL_STATE__` 中取完整段落，不能把动态摘要当作完整原文。

输出不可变的 `manifest.json`、`manifest.sha256`、`preview.md` 和图片文件。检查标题、期号、作者、正文和图片数量。标题超过小黑盒 30 字限制时，仅缩短标题，完整原标题保留在正文开头；保留来源链接及原有署名。图片包括原始封面和正文配图，按顺序插入。`para_type=3` 且 `line={pic:null,line_type:1}` 的分隔线转为可见 `──────────` 段落；其他未知结构仍停止。已有 manifest 直接复用，不再次运行采集覆盖它。

## 账号和发布

阅读 [references/heybox-editor.md](references/heybox-editor.md) 后使用 `node scripts/publish_weekly.cjs`，或在可用浏览器会话中执行相同流程。准备模式在编辑器中核对账号、正文、图片和社区，并保存可重建的本地内容；用户任务已经授权发布时可以直接使用 `--publish` 执行完整流程。已有发布回执时使用 `--verify` 回读核验。

目标账号以文章预览作者或个人主页返回值为准。旧版 MCP 的 `check_login_status` 只检查已经下线的 `p.user-box__username`，可能把实际已登录误报为未登录。使用上述仓库最新版本后，命令会兼容当前顶部导航、用户页和文章作者区域；作者预览显示指定账号且编辑器可用时，以实际页面为准。作者不匹配则停止发布，报告所需登录切换。

小黑盒长周报使用“发布文章”编辑器。批量上传图片后，将正文和已上传图片依原始顺序粘贴为富文本。发布前核对全文、全部图片、精确匹配的社区名称，以及账号身份。仅点击发布按钮不能视为成功，必须查看发布响应和管理列表/帖子详情，取得帖子链接并核对作者和社区。

浏览器连接与启动遵守 [共享会话规则](../weekly-cross-platform-sync/references/browser-session.md)。辅助发布脚本会创建任务专用临时浏览器/context，只有任务已有相应启动授权时才调用；不能影响用户现有窗口。大图先按 [素材压缩与续传](../weekly-cross-platform-sync/references/material-recovery.md) 派生优化图片，批量上传部分失败时按参考说明保存成功映射并只补传失败项；不要直接重跑整个上传批次。

以 `source_author_id + article_id + 目标账号 + 社区 + article` 作为去重键，并保存发布回执到仓库外工作目录。重复运行时先查回执和账号管理页；管理记录必须区分“视频”与“文章”，同一期视频不阻止发布图文文章。发现同一期文章则恢复其公开链接并回读验证，避免再次发布。提交后超时或结果不明时先查管理页与帖子，不能盲目重试发布。

## 跨平台复用

`manifest.json`、`preview.md` 和图片目录是一次采集的统一素材包。若同一周报还要发布到微博或知乎，将这份素材包交给 [weekly-cross-platform-sync](../weekly-cross-platform-sync/SKILL.md) 派生目标 payload；不要为每个平台重新访问 B 站或重复下载图片。平台删减图片、纯文本化正文或截断标题时，只在目标 payload 中记录差异，不能改写源 manifest。

## 交付

最终回复必须直接给出可点击的小黑盒公开帖子链接，附期号、账号、社区和图文核验结果；已有文章核验通过同样给出原链接。缺公开 URL 或回读未通过时不能报告成功。需要登录、审核或人工处理时明确区分“准备完成”“提交待审核”“已公开发布”。团队 skill 的更新仅包含可复用操作和已验证的结构变化，不包含本次账号私密信息或源稿资产。
