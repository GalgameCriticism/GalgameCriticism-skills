# 统一素材清单

素材清单保存在仓库外的任务工作目录。建议字段：

```json
{
  "source": "bilibili|weibo|zhihu",
  "source_id": "账号或作者 ID",
  "article_id": "原文 ID",
  "canonical_url": "https://…",
  "title": "原始标题",
  "author": {"name": "…", "id": "…"},
  "published_at": "ISO-8601",
  "blocks": [{"type": "text|image", "text": "…", "url": "…"}],
  "images": [{"url": "…", "order": 1}],
  "targets": [{"platform": "xiaoheihe|zhihu", "account": "…", "scope": "…"}]
}
```

`article_id` 与来源账号共同组成来源身份；目标账号和社区/话题进入去重键。文件中不写 Cookie、PAT、验证码、浏览器目录或认证请求头。
