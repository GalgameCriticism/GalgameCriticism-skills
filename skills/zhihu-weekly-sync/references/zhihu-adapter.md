# zh_mcp_server 适配说明

上游仓库：<https://github.com/Victorzwx/zh_mcp_server>

当前版本的发布入口名为 `create_atticle`（上游项目保留该拼写），输入包括：

- `title`：文章标题。
- `content`：正文。
- `images`：可选图片参数，当前发布器按封面图片使用。
- `topic`：可选话题。

当前仓库不应保存 `zhihu_cookies.json`、Chrome 用户目录、验证码或发布回执中的私密字段。上游接口返回成功后仍需回读文章页面确认作者和内容状态。
