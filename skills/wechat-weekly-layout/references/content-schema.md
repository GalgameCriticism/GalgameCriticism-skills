# 通用内容结构

`source/article.json` 位于项目根目录的 `source` 下。素材 `path` 相对项目根目录，预览会转换为相对输出文件的路径。每条新闻 ID 唯一，并且恰好归属一个章节。

最小结构如下；`init` 会填写章节素材和封面，新闻由 agent 根据实际原稿添加：

```json
{
  "schema_version": 1,
  "issue": "268",
  "title": "每周 Galgame 新闻速递 第268期",
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
  "staff": ["文案：实际署名", "审核：实际署名", "排版：Agent"],
  "recommendations": [{"title": "真实往期标题", "url": "https://mp.weixin.qq.com/s/实际链接", "image": "previous-cover"}],
  "assets": {
    "cover": {"path": "assets/cover.jpg", "url": "", "width": 1080, "height": 608}
  }
}
```

示例中的其余图片 ID 也必须在 `assets` 登记；推荐文章 URL 是文章链接，不是图片图床地址，应填写核验过的真实文章地址。每个素材需要准确的 `width`、`height`，从图片文件读取，SVG 展开高度依赖此信息。`url` 可省略或仅用于记录来源；渲染器只读取 `path` 对应的本地文件，并将图片字节内嵌到预览和复制结果，完全不要求图床。

`recommendation_banner` 可引用“推荐阅读”章节条，`init` 会一并登记这张品牌素材。

`lead` 是标题下的主图；`gallery.images` 是正文后的补充配图，不包含主图。图组选择：`swipe` 为横向滑动，`fold` 为点击一次展开，`stack` 为纵向平铺。无图组时省略 `gallery` 或用空数组。每个栏目可重新从 1 编号。不存在的 Staff 或推荐可省略，不填写虚构内容。

精确复刻模式另有 `layout`、`images`、`gallery_mode` 字段：`layout` 指向 `theme.json` 中捕获的卡片，`images` 保持其全部图片顺序（含装饰提示图）。这些字段仅用于同一期精确复刻；不传 `--theme` 时渲染器采用通用 `lead` 与 `gallery`。两种模式对图片更改的读取字段不同。

默认 brand 中三个章节条取自用户提供的第 267 期文章；字体为栅格素材。更换栏目名称或设计时，需要同时替换章节图片与素材登记，不只修改 JSON 栏目名。
