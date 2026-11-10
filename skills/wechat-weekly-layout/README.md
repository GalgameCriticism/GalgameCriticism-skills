# wechat-weekly-layout

独立将本地 Word 和图包排成公众号周报，生成能离线打开、一键复制全部正文与图片的预览。支持封面、章节装饰、交替新闻卡、多图交互、往期推荐与 Staff，也可参考已授权的微信文章复刻版式。

只需安装本 skill；不要求图床、公众号 API 密钥、浏览器扩展或其他平台技能。

内部成员先看 [使用手册与任务模板](references/internal-guide.md)。每期请主动提供文稿、封面、图包、推荐阅读的周报及留言板链接、Staff；选择图床方案时另提供图床地址和登录方式/凭证引用。公共 skill 不保存任何真实图床配置或凭证。

如需解决多图 Base64 粘贴失败，可选择 [自建 Zipline 图床导出](references/image-host.md)：先上传并核验 HTTPS 直链，再打开 `preview-hosted.html` 一键复制。图床由使用者指定，凭证运行时读取；支持内部统一分发普通上传账号的 Token。

## 从本地到公众号

安装 Python 依赖：`python3 -m pip install -r <skill>/requirements.txt`。将本期 Word、图包、封面及真实署名交给 agent，按 [SKILL.md](SKILL.md) 生成排版。

1. 双击生成的 `output/preview.html`，或通过本地 HTTP 服务打开它。
2. 点击“复制公众号正文”，正文、样式和本地图片字节一起进入剪贴板。
3. 到公众号正文编辑器粘贴，等待图片处理完成后保存草稿，再检查手机预览。

纯本地模式的预览文件自带所需图片与正文模板，移动单个文件或断网后仍可预览、复制；复制结果不含 `file://`、`localhost` 或远程图片 URL。无需先上传图床。公众号侧的粘贴、图片处理和草稿保存仍由用户完成。

原图保留在本地素材目录；默认对合适的不透明 PNG 生成较小的高质量 JPEG 副本用于复制，保持尺寸，透明图和动画不转换。需要按原图字节复制时加 `--original-images`。旧 `--local-only` 参数仍可接受，所有模式都能复制和导出。

“兼容复制”会把全部配图纵向展开。标准版保留多图交互；本地和通用编辑器验证不代替公众号实际保存回读与手机预览。

## 生成与检查

内容格式见 [content-schema.md](references/content-schema.md)。渲染只依赖 `assets[].path` 本地文件，`url` 仅是可选来源记录。

```bash
python3 <skill>/scripts/wechat_layout.py render --data <project>/source/article.json --out <project>/output
python3 <skill>/tests/test_local_images.py
```

浏览器回归脚本检查内部宽度、图片、折叠和横滑：

```bash
npm install --prefix <skill>/tests playwright
npx --prefix <skill>/tests playwright install chromium
node <skill>/tests/check-layout.mjs http://127.0.0.1:8765/output/article-local.html
node <skill>/tests/check-local-copy.mjs <project>/output/preview.html
```

也可设置 `CHROME_PATH` 使用本机 Chrome。生成器将旧超宽轨道转换为有界 flex 图组，SVG 通过 `viewBox` 动画改变高度，展开时保持宽度不变；窄屏检查包含最后一张图片是否完整。

## 随技能分发的框架图片

六张 PNG 均保存在本目录的 `assets/brand/`，随 skill 一起安装；`init` 会复制到本期本地素材目录，无需联网下载。

| 文件 | 用途 | 尺寸 |
| --- | --- | --- |
| [chapter-new.png](assets/brand/chapter-new.png) | 新作资讯章节条 | 1080 × 90 |
| [chapter-translation.png](assets/brand/chapter-translation.png) | 汉化情报章节条 | 1080 × 90 |
| [chapter-merch.png](assets/brand/chapter-merch.png) | 周边信息章节条 | 1080 × 90 |
| [section-recommended.png](assets/brand/section-recommended.png) | 推荐阅读章节条 | 1080 × 135 |
| [gallery-expand.png](assets/brand/gallery-expand.png) | 点击展开图集提示 | 1080 × 68 |
| [gallery-swipe.png](assets/brand/gallery-swipe.png) | 左滑查看更多提示 | 1080 × 68 |

素材标识、用途和尺寸由 [manifest.json](assets/brand/manifest.json) 记录；新闻卡片的虚线、编号和圆角由内联样式生成。本期封面、新闻配图、往期封面和正文保存在使用者本机，不随 skill 上传仓库。
