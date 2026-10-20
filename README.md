# GalgameCriticism Skills

团队共用的 Agent Skills 仓库，容纳各种各样的 skill。每个 skill 独立放在 `skills/<skill-name>/` 下；本 README 只做目录与仓库级说明，具体 skill 的介绍见各自目录下的 README.md。

仓库级 agent 规则（README 维护约定、提交自检、发布与浏览器约定）见 [AGENTS.md](AGENTS.md)。

## 技能目录

| Skill | 用途 |
| --- | --- |
| [bilibili-weekly-article](skills/bilibili-weekly-article/README.md) | 把期目录 docx 文字稿与图包排版成 B 站图文（Opus），上传配图、生成预览供人工审核，存草稿或直接发布并回读；署名从飞书「周报工作表」按期号拉取 |
| [xiaoheihe-weekly-sync](skills/xiaoheihe-weekly-sync/README.md) | 定位指定期号或最新 B 站周报，保留图文，按文章类型去重，核对小黑盒账号及社区后发布并回读 |
| [weibo-weekly-sync](skills/weibo-weekly-sync/README.md) | 获取获授权微博周报，或将统一素材发布为微博头条文章，处理真实图片校验与失败恢复 |
| [zhihu-weekly-sync](skills/zhihu-weekly-sync/README.md) | 连接独立会话在知乎编辑器内直排周报（标题/正文/逐图上传），核验全文与图片顺序后发布并回读；DOCX 导入受直答知识库配额限制，不作为主链路 |
| [weekly-cross-platform-sync](skills/weekly-cross-platform-sync/README.md) | 统一路由来源与目标平台，管理安装、账号核对、素材清单、去重和回执 |

## 安装

将需要的 skill 文件夹放入客户端的 skills 目录，或在支持 GitHub 安装的客户端中指定本仓库及 `skills/<skill-name>` 路径。支持 OpenAI skill-installer 的环境可以使用：

```bash
python /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo GalgameCriticism/GalgameCriticism-skills \
  --path skills/weekly-cross-platform-sync
```

辅助脚本的依赖写在各 skill 的 SKILL.md 中。账号信息、Cookie 文件、下载的原文与运行记录保留在使用者本机，运行时传入。

## 镜像到独立仓库

若组织下存在与 skill 同名的独立仓库，可用 `scripts/push-org-repos.sh` 把 `skills/<name>/` 的历史（`git subtree split`）推到该仓库的 `main`，monorepo 仍是唯一编辑入口：

```bash
scripts/push-org-repos.sh                        # 全部 skill
scripts/push-org-repos.sh weibo-weekly-sync      # 指定 skill
```

脚本不创建仓库：目标仓库需先在 GitHub 建好，否则会打印「不存在或当前 SSH key 无权限」并跳过。

## 增加技能

新建 `skills/<lowercase-hyphenated-name>/`，包含 `SKILL.md`（frontmatter 的 `name` / `description` 正确）与至少一句定位的 `README.md`，按实际需要添加 `scripts/`、`references/`、`agents/`；**同步更新上方技能目录表格（加一行）**。其余约定（目录口径、提交前脱敏自检、发布与浏览器行为）见 [AGENTS.md](AGENTS.md)。
