# GalgameCriticism Skills

团队共用的 Agent Skills。每个 skill 独立放在 `skills/<skill-name>/` 下，工作流说明、辅助脚本和必要参考资料随 skill 一起维护。

## 技能目录

| Skill | 用途 |
| --- | --- |
| [bilibili-xiaoheihe-weekly](skills/bilibili-xiaoheihe-weekly/SKILL.md) | 定位指定期号或最新 B 站周报，保留图文，按文章类型去重，核对小黑盒账号及社区后发布并回读 |
| [weibo-weekly-sync](skills/weibo-weekly-sync/SKILL.md) | 获取获授权微博周报，或将统一素材发布为微博头条文章，处理真实图片校验与失败恢复 |
| [zhihu-weekly-sync](skills/zhihu-weekly-sync/SKILL.md) | 连接独立会话，以嵌图 DOCX 发布知乎周报，核验全文和图片顺序 |
| [weekly-cross-platform-sync](skills/weekly-cross-platform-sync/SKILL.md) | 统一路由来源与目标平台，管理安装、账号核对、素材清单、去重和回执 |

## 安装

将需要的 skill 文件夹放入客户端的 skills 目录，或在支持 GitHub 安装的客户端中指定本仓库及 `skills/<skill-name>` 路径。支持 OpenAI skill-installer 的环境可以使用：

```bash
python /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo GalgameCriticism/skills \
  --path skills/weekly-cross-platform-sync
```

总工作流会按任务需要调用 `bilibili-xiaoheihe-weekly`、`weibo-weekly-sync`、`zhihu-weekly-sync` 和对应的目标发布适配器；也可以直接安装其中任意一个独立 skill。

辅助脚本的依赖写在各自的 SKILL.md 中。账号信息、Cookie 文件、下载的原文与运行记录保留在使用者本机，运行时传入。

## 增加技能

新建 `skills/<lowercase-hyphenated-name>/SKILL.md`，填写 `name` 和 `description`，按实际需要添加 `scripts/`、`references/`、`agents/`。在上面的技能目录添加一行，并验证 frontmatter、脚本和凭证脱敏。请勿将某位成员的用户名路径、令牌、Cookie、浏览器配置目录或运行产物提交到仓库。

工作流里涉及发布时，以用户授权的来源、账号和目标范围为准；说明发布前验证、结果核验和重复发布的处理方式。

发布完成后的最终回复必须直接提供每个成功平台的可点击公开文章链接；部分失败时也列出已成功链接及其余平台状态。浏览器优先连接独立会话；用户明确授权自动启动时可启动同一专用 profile，始终不重置或清理登录态。
