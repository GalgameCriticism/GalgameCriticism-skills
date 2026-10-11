# mcp-server-weibo 适配说明

上游仓库：<https://github.com/qinyuanpei/mcp-server-weibo>

当前工作流依赖的读取工具名称包括：

- `search_users`：按关键词解析微博用户。
- `get_profile`：核对用户身份。
- `get_feeds`：获取用户动态并按时间筛选周报。
- `search_content`、`search_topics`：按关键词补充来源。
- `get_comments`：仅在周报正文需要上下文时使用。

工具名称或返回字段可能随上游更新变化；调用前以已安装 MCP 的工具列表为准。不要在此文件记录 Cookie、session、账号密码或运行时绝对路径。
