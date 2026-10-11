# 小黑盒长文章工作流

## 本机配置

使用者准备自己的 Cookie 文件；兼容 Playwright 的小写字段，也兼容 .NET Newtonsoft 序列化的 `Name`、`Value`、`Domain`、`Path`、`Expires`、`HttpOnly`、`Secure`、`SameSite`。后者的 SameSite 数字枚举为 `0=Strict`、`1=Lax`、`2=None`。Cookie 值只传入浏览器 context，不打印。

```bash
export XIAOHEIHE_COOKIE_PATH=/private/local/path/account.json
export XIAOHEIHE_CHROMIUM_PATH=/path/to/chromium
# 若环境已有 Playwright 驱动，可直接引用其包目录；否则安装 playwright-core。
export PLAYWRIGHT_MODULE_PATH=/path/to/playwright-core

python3 scripts/fetch_weekly.py '<文集URL>' --output /local/work/weekly
node scripts/publish_weekly.cjs /local/work/weekly/manifest.json \
  --account '<目标账号名称>' --community '<目标社区>'
# 用户已明确要求发布时使用 --publish。
# 核验已有回执且不发布：追加 --verify。
```

输出文件放仓库外。`.NET` MCP 的浏览器 context 在进程内共享，改变 Cookie 路径后必须重建进程/context 才会加载新账号。默认账号切换优先设置客户端条目的 `env.XIAOHEIHE_COOKIE_PATH`；对默认 `data/cookies.json` 的替换要先保留原账号文件。不要将不同 Cookie 文件混合成一个账号。

## 页面位置与验证

- 编辑器：`https://www.xiaoheihe.cn/creator/editor/draft/article`，会重定向到本地草稿地址。
- 内容管理：`https://www.xiaoheihe.cn/creator/content_management/home?article_type=all`。
- 个人主页：`/app/user/profile/<用户ID>`；省略 ID 会回到首页。
- 登录后的顶部头像菜单显示账号名称/ID，文章预览作者为 `.bbs-link-section-author-name`。
- `.ProseMirror` 第一个为标题，第二个为正文；标题限制 30 字。

发布前到内容管理页检查同一期标题（包括期号）或来源链接，已有本期时回读验证。管理页只显示近期内容，不应据此推断旧文章不存在；同步历史一期时继续翻页或使用已有回执。

## 图片和正文

正文聚焦后点击 `.editor-menu-image__btn`，在插图弹窗点击 `.editor-image-wrapper__box.upload`，捕获 filechooser。它支持多文件；把完整图片集一次性传入，避免前一个批次未完成就新增批次导致插图状态异常。等待所有 `.editor-image-wrapper__box.draggable img` 出现且 `.editor-image-wrapper__box-uploading` 清零，再点击确定。

图片源 URL 来自弹窗的已完成图片元素，保留原始顺序。大量图片会遮住弹窗底部，可对已经确认的确定按钮调用 DOM `click()`。

通过富文本 paste 事件插入正文，图片用编辑器自身序列化形式 `<p><img data-type="image" data-original="已上传URL" data-width="宽" data-height="高"></p>`。普通 `<img src="...">` 会触发额外的粘贴图片上传并造成重复图片。直接修改 `innerHTML` 不保证编辑器状态同步。粘贴后比较所有正文字符（忽略排版空白）、图片数量和图片 URL 顺序；编辑器的一级/二级章节分别对应 `h2`/`h3`。

社区搜索必须找到唯一精确名称匹配，再核对已选社区。旧 MCP 直接点击第一项并不能保证选中指定社区。作者、标题、正文、图片或社区任何一项未验证通过时，不提交。

## 发布结果

发布请求、图片上传请求可能包含 Cookie、签名、短期上传令牌；只记录状态码、结果状态、帖子 ID 和必要的公开信息，禁止输出完整请求、响应或 HAR。

一次点击发布后，`POST /bbs/app/api/link/post` 成功响应包含 `status: "ok"` 和 `link_id`。取得 `/app/bbs/link/<link_id>` 后，核验内容管理新记录和帖子详情；详情作者为 `.link-user__username`，社区为 `.link-tags__tag-item .content-tag-text`，正文为 `.hb-article`。图片按滚动位置懒加载，先逐张滚入视口，再核对 URL。公开页面会将原图 `/<hash>.png` 转为 `/<hash>/thumb.png`；按原图标识归一化后比较顺序。

本地输出 `uploaded-images.json` 与 `publication-receipt.json`。准备模式只保存可重建内容的本地文件；再次执行复用上传 URL 并重建编辑器，不依赖上一次会话的本地草稿。提交前将回执写为 `submitting`，服务端响应确认后写入帖子 URL；结果不明时脚本退出并拒绝再次提交。已有帖子 URL 时，`--publish` 也只回读核验，不重复发布。

若返回审核状态，报告待审核并保留回执，避免重复提交。页面超时但可能提交成功时先查内容管理。Cookie 未过期不等于有效登录，最终以真实页面账号身份为准。
