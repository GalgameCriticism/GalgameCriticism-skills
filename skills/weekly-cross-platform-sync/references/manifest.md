# 统一素材清单

素材清单保存在仓库外的任务工作目录。建议字段：

```json
{
  "source": "bilibili|weibo|zhihu",
  "source_id": "来源作者ID:来源文章ID",
  "article_id": "原文 ID",
  "canonical_url": "https://…",
  "title": "原始标题",
  "author": {"name": "…", "id": "…"},
  "published_at": "ISO-8601",
  "blocks": [{"type": "paragraph", "nodes": [{"text": "…", "marks": []}]}, {"type": "image", "url": "…", "path": "images/001.jpg", "order": 1, "sha256": "…"}],
  "images": [{"url": "…", "path": "images/001.jpg", "order": 1, "sha256": "…"}]
}
```

`source_id` 标识来源内容，不是单独的账号 ID；`article_id` 与来源账号共同组成来源身份。完整原标题另存 `source_title`，平台短标题存目标 payload。目标账号、范围、内容类型和 manifest SHA-256 写入各目标 payload 和回执。既有 B 站辅助脚本的 `source_url`、`source_author_id` 等兼容字段可以保留。

首次生成后保存 `manifest.sha256`，不覆盖源 manifest；压缩图、DOCX 和平台 payload 都是派生产物。文件中不写 Cookie、PAT、验证码、浏览器目录或认证请求头。

## 发布回执及最终链接

一个任务保存各目标的最小状态，例如：

```json
{
  "source_id": "来源作者ID:来源文章ID",
  "manifest_sha256": "…",
  "targets": [{
    "platform": "weibo|zhihu|xiaoheihe",
    "account": "目标账号",
    "scope": "目标社区或文章范围",
    "content_type": "article",
    "status": "published",
    "url": "实际公开文章HTTPS链接",
    "title": "实际发布标题",
    "full_text_verified": true,
    "images": 1,
    "image_order_verified": true,
    "source_preserved": true,
    "verified_at": "ISO-8601"
  }]
}
```

`published` 必须同时具备公开 `url`、正确账号/范围、全文及全部图片顺序的回读证据。旧平台回执的 `postUrl`、`articleUrl` 应在汇总时映射到统一 `url`。提交前先写 `submitting`，确认收到服务端文章 ID 后写 `submitted` 和 URL，公开核验后才改为 `published`。没有 URL 或尚未回读的目标不能为了填完整表而标成功。

最终回复从已核验 `published` 项生成平台链接列表：`- 平台：[本期文章](该项url)`。此列表是必填交付，不以本地回执下载链接代替。部分失败时仍输出所有成功平台的公开链接，并保留其他目标的 `pending_review`、`unknown` 或 `failed` 状态及原因。
