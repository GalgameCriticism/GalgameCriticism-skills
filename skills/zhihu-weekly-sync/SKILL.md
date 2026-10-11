---
name: zhihu-weekly-sync
description: 使用 zh_mcp_server 将用户拥有或获授权的周报素材发布到知乎，完成账号核对、草稿预览、发布和结果验证；需要从知乎转出内容时也用于判断上游能力边界。
---

# 知乎周报同步

本 skill 是知乎发布端适配器：把经核验的周报素材发布为知乎文章。素材可以来自 B 站、微博或用户提供的知乎文章 URL；发布授权来自当前任务，目标账号必须在发布前核对。

## 前置依赖：安装知乎 MCP

使用上游项目 [Victorzwx/zh_mcp_server](https://github.com/Victorzwx/zh_mcp_server)：

```bash
git clone https://github.com/Victorzwx/zh_mcp_server.git
cd zh_mcp_server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m zh_mcp_server.__login__
```

登录脚本会打开 Chrome，并在终端等待验证码；Cookie 只放在本机。stdio 配置使用虚拟环境中的 Python：

```json
{
  "mcpServers": {
    "zh_mcp_server": {
      "command": "/absolute/path/to/zh_mcp_server/.venv/bin/python",
      "args": ["-m", "zh_mcp_server"]
    }
  }
}
```

当前上游代码实际将 `zhihu_cookies.json` 放在 Python 包目录附近；`json_path` 不能替代对实际 Cookie 文件位置的检查。登录后确认文件位于本机私有目录并限制权限，绝不将虚拟环境、Cookie 或登录输出提交到团队仓库。

## 工作流

1. 接收统一素材清单，核对标题、正文、图片顺序、署名、来源链接和目标知乎账号；标题和正文未确认时只生成预览。
2. 先用知乎浏览器会话或上游服务确认当前登录账号，再调用上游工具。工具名沿用项目当前的拼写 `create_atticle`，参数为 `title`、`content`、可选 `images` 和 `topic`。
3. 由于当前上游发布接口只支持一个封面图片参数，正文中的多图应先按目标格式整理；不能声称所有原图都已作为知乎正文图片上传。若素材要求保留全量图片，先报告能力限制并等待目标格式确认。
4. 发布后回读知乎文章 URL、标题、作者和封面；无法取得公开 URL 或账号不匹配时，不把提交响应单独当作成功。

## 能力边界

`zh_mcp_server` 当前是知乎自动发文章服务，不提供可靠的“读取某账号最新文章/周报列表”工具。因此“从知乎搬运最新一期”必须由用户提供文章 URL/正文，或接入另一个经过验证的读取适配器；不能用 `create_atticle` 反推来源内容。将 B 站或微博周报同步到知乎属于本 skill 的正常用法。

## 去重与核验

以来源平台、来源内容 ID、目标知乎账号组成去重键；先查仓库外回执和目标账号文章列表，再决定发布或回读。回执记录标题、来源 URL、目标账号、文章 URL、封面状态和核验时间，不记录 Cookie 或令牌。
