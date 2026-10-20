# 知乎图文文章适配说明

## 会话与身份

用一个专用 profile 的 Chrome（CDP 端口默认 `9444`），由 `scripts/browser-session.cjs` 的 `attach()` 复用同一窗口，不逐步开关浏览器。身份以 `/api/v4/me` 的 `name` 为准，必须等于目标账号（`Galgame批评`）；只记录公开身份，不输出完整响应。CDP 端口是运行时配置，不能硬编码到团队 skill（可用 `ZHIHU_DEBUG_PORT` 覆盖）。

## 直排正文（默认路径）

`scripts/zhihu-compose.cjs` 做三件事：填标题、逐块粘贴正文、按 manifest 顺序逐张上传图片。

- 标题输入：`textarea[placeholder*="标题"]`，内容用 manifest 的 `source_title`（正文里重复的那一行标题块要跳过）。
- 正文粘贴：向 `.public-DraftEditor-content[contenteditable="true"]` 派发带 `text/html` 的 `ClipboardEvent('paste')`；标题层级用 `Meta+Alt+<level>` 切换，再 `Enter` 开新段。
- 图片：每张图通过 `input[type=file][accept*="image"]` 的 `setInputFiles` 上传，位置由当前光标决定，因此必须严格按 manifest 的块顺序推进。

### 图片完成判定

托管地址特征是 `/v2-[0-9a-f]{32}`。不要用 `zhimg.com` 域名判断：占位/预览阶段也会出现 zhimg 前缀，但 `src` 仍是 `blob:` 或空串，会误判成功。

### 不要做“重试上传”

上传慢是常态（实测单张可达数分钟）。把同一路径重新 `setInputFiles` 会再插一张图，正文图片数直接翻倍；脚本里 `attempt <= 1` + 长时间等待是刻意设计。确实失败时先核对编辑器里是否已经多出一张，再决定补传。

### 校验

- 图片数 = manifest 图片块数，且全部是真实 HTTPS 托管地址。
- 归一化全文与 manifest 逐字一致，剔除“添加图片注释，不超过140字（可选）”这类编辑器 UI 文案。
- 正文不能残留 `![配图](...)`、`images/001.png`、`WBIMGPH_` 等占位。
- 封面用 `.UploadPicture-input`，必须显示 zhimg 托管地址；封面不计入正文图片数。

## DOCX 导入（备用，当前账号被拦）

`导入` → `导入文档` → 选择 `.docx` 这条链路在 2026-10 的第265期实测被**直答知识库配额**拦截：文件能被选中并进入上传，但“确认选择文件”永不进入可点击态。已尝试并失败的替代做法包括：隐藏 file input 直接 `setInputFiles`、真实鼠标坐标点击、点击行内单选按钮、点击行内 label、等待上传完成后再点确认。这些都不要重复尝试。

只有当直排不可用且确认配额恢复时才回到 DOCX：先按 UI 大小限制预检字节数，超限则从原 manifest 派生压缩图片重建 DOCX；导入后等“文档导入中”结束，再核对 `word/media/`、正文嵌图对象和顺序。

## 提交与公开页

- 编辑页点“发布”→ 若出现确认弹窗，点最后一个“发布”→ 监听 `/api/v4/content/publish`，取 `data.id`。
- 走草稿箱时用 `scripts/zhihu-draft-publish.cjs`：逐个打开草稿（“编辑”可能新开标签页，要跟随新页面），挑正文与图片完全匹配的那一篇再发布，避免产生第二篇。
- 公开页正文在 `.Post-RichTextContainer .RichText`；作者 `.AuthorInfo-name`，标题 `h1.Post-Title`。
- 知乎图片 URL 的 host、`_r`/`_720w` 等规格可变；按 `v2-<hash>` 比较原序号，不把 URL 字符串变体误报为顺序错误。
- 只有拿到 `https://zhuanlan.zhihu.com/p/<id>` 且回读通过才算成功；请求 200 或本地回执都不算。

## 旧 MCP 的兼容边界

上游仓库：<https://github.com/Victorzwx/zh_mcp_server>

发布入口名为 `create_atticle`（上游保留该拼写），参数：`title`、`content`、可选 `images`（按封面使用）、`topic`。

当前仓库不应保存 `zhihu_cookies.json`、Chrome 用户目录、验证码或发布回执中的私密字段。上游接口返回成功后仍需回读文章页面确认作者和内容状态。
