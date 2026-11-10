# 通用内容结构

`source/article.json` 位于项目根目录的 `source` 下。素材 `path` 相对项目根目录，预览会转换为相对输出文件的路径。每条新闻 ID 唯一，并且恰好归属一个章节。

最小结构如下；`init` 会填写章节素材和封面，新闻由 agent 根据实际原稿添加：

```json
{
  "schema_version": 1,
  "issue": "<期号>",
  "title": "本期周报标题",
  "subtitle": "本期实际头条",
  "account": "Galgame批评",
  "cover": "cover",
  "sections": [
    {"name": "新作", "banner": "chapter-new", "stories": ["news-01"]}
  ],
  "stories": [{
    "id": "news-01",
    "number": 1,
    "title": "原稿新闻标题",
    "paragraphs": ["原稿第一段。", "原稿第二段。"],
    "lead": "hero-01",
    "gallery": {"mode": "fold", "images": ["cg-01", "cg-02"]}
  }],
  "staff": ["文案：用户确认的署名", "文案审核：用户确认的署名", "排版：用户确认的署名"],
  "recommendations": [
    {"title": "用户提供的往期周报标题", "url": "https://mp.weixin.qq.com/s/周报链接", "image": "previous-cover"},
    {"title": "用户提供的留言板标题", "url": "https://mp.weixin.qq.com/s/留言板链接", "image": "message-board-cover"}
  ],
  "assets": {
    "cover": {"path": "assets/cover.jpg", "url": "", "width": 1080, "height": 608}
  }
}
```

示例中的其余图片 ID 也必须在 `assets` 登记；推荐文章 URL 是文章链接，不是图片图床地址，应填写核验过的真实文章地址。每个素材需要准确的 `width`、`height`，从图片文件读取，SVG 展开高度依赖此信息。`url` 可省略或仅用于记录来源；渲染器只读取 `path` 对应的本地文件，并将图片字节内嵌到预览和复制结果，完全不要求图床。

`recommendation_banner` 可引用“推荐阅读”章节条，`init` 会一并登记这张品牌素材。

`lead` 是标题下的主图；`gallery.images` 是正文后的补充配图，不包含主图。图组选择：`swipe` 为横向滑动，`fold` 为点击一次展开，`stack` 为纵向平铺。无图组时省略 `gallery` 或用空数组。每个栏目可重新从 1 编号。推荐阅读的周报/留言板链接与 Staff 先请用户提供，用户明确不放某项时再省略；不填虚构内容。推荐封面由用户提供或从其授权的推荐文章提取，须登记到本地素材。

精确复刻模式另有 `layout`、`images`、`gallery_mode` 字段：`layout` 指向 `theme.json` 中捕获的卡片，`images` 保持其全部图片顺序（含装饰提示图）。这些字段仅用于同一期精确复刻；不传 `--theme` 时渲染器采用通用 `lead` 与 `gallery`。两种模式对图片更改的读取字段不同。

`gallery_hints` 可按 `{"fold": "gallery-expand", "swipe": "gallery-swipe"}` 指定图集提示图，`init` 自动填入。缺少配置时可退回文字提示；兼容版纵向展开后不显示交互提示。`gallery.images` 只有一张时始终直接展示，不应用滑动或折叠模板，也不显示交互提示。

默认 brand 中六张框架素材取自用户提供的参考文章，随技能本地分发；字体为栅格素材。更换栏目名称或设计时，需要同时替换章节图片与素材登记，不只修改 JSON 栏目名。

普通静态配图默认转为 ≤500 KiB 的 JPG，透明正文配图合成白底。仅装饰素材应填写 `assets[].role`（如章节条、图集提示），以保留其透明背景和原格式；不要给正文配图填写装饰 role 来绕过白底处理。装饰与动图同样须达标，超限会停止。
