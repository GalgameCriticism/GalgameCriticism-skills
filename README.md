# GalgameCriticism Skills

团队共用的 Agent Skills。每个 skill 独立放在 `skills/<skill-name>/` 下，工作流说明、辅助脚本和必要参考资料随 skill 一起维护。

## 技能目录

| Skill | 用途 |
| --- | --- |
| [bilibili-xiaoheihe-weekly](skills/bilibili-xiaoheihe-weekly/SKILL.md) | 从 B 站文集确定最新一期，保留正文和配图，核对小黑盒账号及社区后发布并验证结果 |

## 安装

将需要的 skill 文件夹放入客户端的 skills 目录，或在支持 GitHub 安装的客户端中指定本仓库及 `skills/<skill-name>` 路径。支持 OpenAI skill-installer 的环境可以使用：

```bash
python /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo GalgameCriticism/skills \
  --path skills/bilibili-xiaoheihe-weekly
```

辅助脚本的依赖写在各自的 SKILL.md 中。账号信息、Cookie 文件、下载的原文与运行记录保留在使用者本机，运行时传入。

## 增加技能

新建 `skills/<lowercase-hyphenated-name>/SKILL.md`，填写 `name` 和 `description`，按实际需要添加 `scripts/`、`references/`、`agents/`。在上面的技能目录添加一行，并验证 frontmatter、脚本和凭证脱敏。请勿将某位成员的用户名路径、令牌、Cookie、浏览器配置目录或运行产物提交到仓库。

工作流里涉及发布时，以用户授权的来源、账号和目标范围为准；说明发布前验证、结果核验和重复发布的处理方式。
