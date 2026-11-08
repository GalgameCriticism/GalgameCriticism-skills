---
name: wechat-weekly-layout
description: 从本地 Word 和图包排版公众号周报，生成可离线打开、一键复制全部图文的预览与内嵌图片 HTML，支持封面、章节装饰、多图交互、往期推荐和 Staff；也可参考已授权微信文章复刻版式。
---

# 公众号周报排版

用中文沟通。默认流程是「本地文字稿与图片 → 本地排版 → 打开预览一键复制 → 粘贴公众号」。交付可离线独立打开的 `preview.html`、可编辑内容 JSON、内嵌图片的正文 HTML 和折叠区展开版。保留文字稿内容与图片归属，按用户的参考和反馈调整样式。

脚本路径均相对本 skill 目录：`scripts/wechat_layout.py`。依赖见 `requirements.txt`（`beautifulsoup4`、`requests`、`Pillow`）；浏览器预览和截图使用可用的 Chromium/Playwright。生成器只读本地图片并写本地产物，不登录、不上传图床、不发布公众号。`assets[].url` 只是可选来源元数据，不参与渲染或复制；图片以 `assets[].path` 指向的真实本地文件为准。

## 复刻一篇已有微信文章

先读参考文章的实际 HTML，检查 `#js_content`、章节条、卡片、图片与交互；微信标题、Staff 等可能绘制在图片里，正文文本提取不能替代视觉查看。

```sh
python3 <skill>/scripts/wechat_layout.py capture --url '<文章 URL>' --out <project>/reference/article.html
python3 <skill>/scripts/wechat_layout.py import-reference --html <project>/reference/article.html --docx '<文字稿.docx>' --url '<文章 URL>' --out <project>
python3 <skill>/scripts/wechat_layout.py render --data <project>/source/article.json --theme <project>/source/theme.json --out <project>/output
```

此导入器针对已验证的 Galgame 批评周报结构：三个栏目“新作／汉化／周边”，新闻标题使用 `strong`、编号使用 `b`，正文位于 15px 字号的容器中。它按标题一一对应 Word，优先使用原稿正文；原稿的“（简）”是编辑标记，展示标题沿用已发布文章。遇到其他结构先检查 DOM、调整提取，不把未验证的结果当作成功复刻。

`capture` 使用移动端 UA，成功标准是正文存在。若仍为验证页，使用用户提供的已保存 HTML 或实际可访问的浏览器页面，不用验证页充当参考。原稿若只有文字，优先从用户提供且拥有或获授权的同一期文章补齐素材；缺图则明确列出。

导入生成的 `theme.json` 保存原文组件和 SVG，不依赖秀米服务。渲染时会把原文超宽轨道转换为有界 flex 图组，并把 SVG 宽度动画转换为改变高度的 `viewBox` 动画；这些兼容性修正优先于逐字保留旧 HTML。原文 Staff 保留文案与审核署名，复刻稿的排版标记为 Agent，并注明原版式设计者。同一期调整文字可编辑 `article.json` 再渲染；精确模式的新闻图片按 `images` 数组映射，固定布局中的封面、章节、Staff、推荐需同步修改 theme。跨期改用下述通用模式，避免旧期信息混入。

## 下一期从文字稿和图包生成

读取 [内容结构与素材映射](references/content-schema.md)，按其格式组织 JSON。初始品牌素材含三个栏目条与“推荐阅读”章节条，不含旧期新闻配图或封面。

```sh
python3 <skill>/scripts/wechat_layout.py extract-docx '<文字稿.docx>' --out <project>/source/paragraphs.json
python3 <skill>/scripts/wechat_layout.py init --out <project> --issue '<期号>' --title '<本期标题>' --cover '<本期封面图片>'
```

结合 Word 的标题、段落、空行和图包人工语义映射章节与每条新闻，填写 `source/article.json`。正文逐段保存，不擅自改写价格、日期、人名或校对原稿事实；疑似笔误单独提示。无字幕的图包按文件名、缩略图和作品内容对应，歧义未解决前不要把不相干图片配上。

用脚本的通用组件生成；此模式不传 `--theme`：

```sh
python3 <skill>/scripts/wechat_layout.py render --data <project>/source/article.json --out <project>/output
```

通用卡片沿用参考文章的绿色／粉色虚线交替样式，支持 `swipe`、`fold`、`stack` 图组。封面必须对应本期：原封面内的期号和插画是图片内容，修改 JSON 不会修改图片；使用本期成品封面，或按参考另行制作。

所有渲染产物都默认使用本地图片；没有 `url` 也能生成、预览和复制。旧参数 `--local-only` 仅为命令兼容保留，不再限制复制或导出。复制和 HTML 中的图片使用内嵌 `data:image/...;base64,...` 字节，不能写成 `file://`、`localhost` 或图床地址。

预览文件内保存本地图片数据与正文模板，复制按钮不再 `fetch` 正文或图片；双击单个预览文件也可用。为减少多图剪贴板体积，默认对较大的、不透明、非动画 PNG 生成 JPEG 94 质量副本，保持尺寸，透明图片和动画原样保留；原图不覆盖。需要逐字节保留图片时传 `--original-images`。派生副本放输出目录的 `clipboard-images/`，不入技能仓库。

## 预览与完成标准

直接在浏览器打开 `output/preview.html`，点击“复制公众号正文”，随后粘贴到公众号。也可启动本地 HTTP 服务展示预览，但它不是复制图片的依赖；正文不从服务读取图片。粘贴后等待公众号完成图片处理，再保存草稿并核验。

交付前检查：

- 原稿每条新闻及正文段落完整，对应章节、标题、图片正确；往期推荐链接真实，Staff 署名有据可查。
- 在 320px、375px、430px 手机宽度以及桌面宽度查看封面、章节、长标题、混合日文、长正文、尾部。所有图片加载成功；去除正文外层裁切后，整页和内部各元素仍不得超过父级宽度。可用 `tests/check-layout.mjs <纯正文预览URL>` 执行回归。
- 对实际折叠区点击，确认高度增长、最后一张图显示完整；横向图组可滑至末图。通用 SVG 的高度依据图片宽高计算，不复制上一组的固定百分比；展开前后宽度保持不变。新组件用 `viewBox` 动画改变固有纵横比，避免使用超过 100% 的宽度动画。
- 复制后读取剪贴板 `text/html`，并在可用时实际粘贴到通用 contenteditable 复查内部宽度；确认所有图片均为内嵌数据，SVG 与内联样式仍在，且未混入预览页控件。正式正文不含 JavaScript、外链 CSS 或普通网页 `details` 交互。
- 在禁止外网请求的环境下检查预览和复制；再断开网络，直接打开单个 HTML 文件并实际粘贴到通用 contenteditable，核对全部图片可解码、顺序及正文完整。复制不能依赖图床 URL、本地服务存活或其他图片文件。透明图和 GIF 的字节保真回归见 `tests/test_local_images.py`；`tests/check-local-copy.mjs <preview.html>` 会把单个预览复制到独立临时目录，断网后检查两种复制按钮与原生粘贴。
- 本地浏览器检查与公众号编辑器检查分别记录。未经过“粘贴到草稿→保存→重新读取→手机预览”时，明确交代尚未验证微信编辑器保留效果。同时提供 `wechat-expanded.html` 作为折叠区展开版，以及 `wechat-safe.html`／预览页“兼容复制”作为全部图片纵向展开、没有 SVG 或横滑的备选。

`output/validation.json` 记录结构检查，不代表视觉检查或微信端验收。提供预览入口和需要的导出文件，简要说明验证结果与实际限制。
