# 公众号排版 Skill 使用手册

把下面这句话发给支持 Skill 的 AI 客户端：

> 从 https://github.com/GalgameCriticism/GalgameCriticism-weekly-text-publishing-skills 拉取并安装 skills/wechat-weekly-layout，仅安装公众号 skill，同时安装其 requirements.txt 中的依赖。

安装后调用：

> 使用 wechat-weekly-layout 排版我提供的本期 Word、封面和图包。推荐阅读的周报与留言板链接、Staff 由我提供；图片默认使用本地复制。

更新时告诉 AI：从同一仓库更新 wechat-weekly-layout。安装后未显示技能时，重新打开会话。

使用图床时，请由管理员提供：图床产品与版本、HTTPS 公网地址、普通账号及 API Token 获取方式。凭证保存到本机环境变量、钥匙串或私密文件，向 AI 提供凭证位置即可；不要填写在公共 skill 中。

> 本期改用图床方案：产品/版本为……，HTTPS 地址为……，登录方式为……，凭证保存在……。请先上传并核验图片，再生成图床复制预览。
