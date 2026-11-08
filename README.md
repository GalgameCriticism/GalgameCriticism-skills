# GalgameCriticism 周报文字版发布 Skills

面向周报文字版与图文版的发布技能集合，按目标平台并列维护。每个平台的执行说明、脚本和参考都放在自己的 `skills/<skill-name>/` 内，可以按需单独安装，无需安装总调度 skill。

仓库地址：<https://github.com/GalgameCriticism/GalgameCriticism-weekly-text-publishing-skills>。仓库维护约定见 [AGENTS.md](AGENTS.md)。

## 技能目录

| 平台 | Skill | 用途 |
| --- | --- | --- |
| 微信公众号 | [wechat-weekly-layout](skills/wechat-weekly-layout/README.md) | 将 Word 与本地图包排成带装饰与多图交互的公众号 HTML，支持离线预览及一键复制全部图文，无需图床。 |
| B 站 | [bilibili-weekly-article](skills/bilibili-weekly-article/README.md) | 将文字稿与图包制作成 B 站图文，核对署名、预览并提交草稿或发布。 |
| 小黑盒 | [xiaoheihe-weekly-sync](skills/xiaoheihe-weekly-sync/README.md) | 从授权来源或素材包发布小黑盒周报，核对账号、社区及去重状态。 |
| 微博 | [weibo-weekly-sync](skills/weibo-weekly-sync/README.md) | 从授权来源或素材包编排微博头条文章，发布并回读正文与图片。 |
| 知乎 | [zhihu-weekly-sync](skills/zhihu-weekly-sync/README.md) | 从授权素材包直排知乎文章，核验账号、全文与图片顺序后发布。 |

## 按需安装

只安装目标平台对应的一行即可。使用支持 GitHub 的 skill 安装器时，指定本仓库和该 skill 的完整路径，例如只安装公众号：

```bash
python /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo GalgameCriticism/GalgameCriticism-weekly-text-publishing-skills \
  --path skills/wechat-weekly-layout
```

安装其他平台时，将最后一行换为 `skills/bilibili-weekly-article`、`skills/xiaoheihe-weekly-sync`、`skills/weibo-weekly-sync` 或 `skills/zhihu-weekly-sync`。需要多个平台时可分别安装，各目录没有相互加载要求。

也可以下载或克隆仓库，将选中的 `skills/<skill-name>/` 整个目录复制到客户端的 skills 目录。依赖、账号准备与使用示例见各平台自己的 README；无需复制本仓库全部技能。

## 维护与隐私

账号、Cookie、浏览器登录态、下载的原文和运行产物保存在使用者本机，运行时传入。新增或删除技能时同步更新上表；脚本、测试、素材与平台细节放在对应 skill 内，不放仓库根。发布仅作用于用户授权的账号与范围，并以平台回读结果确认完成。
