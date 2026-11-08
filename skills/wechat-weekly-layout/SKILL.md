---
name: wechat-weekly-layout
description: 将公众号周报的 Word 文字稿和图包排成带封面、章节、装饰新闻卡、多图滑动或点击展开、往期推荐与 Staff 的富文本 HTML；也可读取用户提供的微信文章复刻版式。用于公众号周报排版和替代秀米的本地生成流程。
---

# 公众号周报排版

用中文沟通。交付可审阅的本地预览、可编辑内容 JSON、公众号正文 HTML 和折叠区展开版。保留文字稿内容与图片归属，按用户的参考和反馈调整样式。

脚本路径均相对本 skill 目录：`scripts/wechat_layout.py`。依赖见 `requirements.txt`（`beautifulsoup4`、`requests`、`Pillow`）；浏览器预览和截图使用可用的 Chromium/Playwright。生成器只写本地产物，不登录、上传或发布公众号。

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
python3 <skill>/scripts/wechat_layout.py render --data <project>/source/article.json --out <project>/output --local-only
```

通用卡片沿用参考文章的绿色／粉色虚线交替样式，支持 `swipe`、`fold`、`stack` 图组。封面必须对应本期：原封面内的期号和插画是图片内容，修改 JSON 不会修改图片；使用本期成品封面，或按参考另行制作。

`--local-only` 可先使用本地图片审稿，复制和公众号导出会禁用。真实微信图床 HTTPS URL 写回素材表后，去掉该参数生成正式 HTML。图床上传按用户实际授权和可用工具执行；不要虚构 URL，也不要擅自把素材上传公开服务。

## 预览与完成标准

在项目目录启动本地 HTTP 服务，如 `python3 -m http.server 8765 --bind 127.0.0.1`，展示 `http://127.0.0.1:8765/output/preview.html`；从 HTTP 页面使用“复制公众号正文”。

交付前检查：

- 原稿每条新闻及正文段落完整，对应章节、标题、图片正确；往期推荐链接真实，Staff 署名有据可查。
- 在 320px、375px、430px 手机宽度以及桌面宽度查看封面、章节、长标题、混合日文、长正文、尾部。所有图片加载成功；去除正文外层裁切后，整页和内部各元素仍不得超过父级宽度。可用 `tests/check-layout.mjs <纯正文预览URL>` 执行回归。
- 对实际折叠区点击，确认高度增长、最后一张图显示完整；横向图组可滑至末图。通用 SVG 的高度依据图片宽高计算，不复制上一组的固定百分比；展开前后宽度保持不变。新组件用 `viewBox` 动画改变固有纵横比，避免使用超过 100% 的宽度动画。
- 复制后读取剪贴板 `text/html`，并在可用时实际粘贴到通用 contenteditable 复查内部宽度；确认图片 URL、SVG 与内联样式仍在，且未混入预览页控件。正式正文不含 JavaScript、外链 CSS 或普通网页 `details` 交互。
- 本地浏览器检查与公众号编辑器检查分别记录。未经过“粘贴到草稿→保存→重新读取→手机预览”时，明确交代尚未验证微信编辑器保留效果。同时提供 `wechat-expanded.html` 作为折叠区展开版，以及 `wechat-safe.html`／预览页“兼容复制”作为全部图片纵向展开、没有 SVG 或横滑的备选。

`output/validation.json` 记录结构检查，不代表视觉检查或微信端验收。提供预览入口和需要的导出文件，简要说明验证结果与实际限制。
