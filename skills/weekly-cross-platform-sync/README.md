# weekly-cross-platform-sync

统一路由来源与目标平台，管理安装、账号核对、素材清单、去重和回执；把已发布的 B 站周报图文分发到小黑盒、知乎、微博等平台。

Agent 执行说明见 [SKILL.md](SKILL.md)。

在周报生产链路中的位置（第二段）：接收已发布的 B 站图文（cv 号），采集一次不可变素材清单后，调用各平台 skill 完成搬运。链路全景见 [bilibili-weekly-article 的 README](../bilibili-weekly-article/README.md)。
