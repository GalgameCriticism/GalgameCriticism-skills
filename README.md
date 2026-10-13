# GalgameCriticism Skills

团队共用的 Agent Skills 仓库，容纳各种各样的 skill。每个 skill 独立放在 `skills/<skill-name>/` 下；本 README 只做目录与仓库级说明，具体 skill 的介绍见各自目录下的 README.md。

仓库级 agent 规则（README 维护约定、提交自检、发布与浏览器约定）见 [AGENTS.md](AGENTS.md)。

## 技能目录

- [bilibili-weekly-article](skills/bilibili-weekly-article/README.md)
- [weekly-cross-platform-sync](skills/weekly-cross-platform-sync/README.md)
- [xiaoheihe-weekly-sync](skills/xiaoheihe-weekly-sync/README.md)
- [weibo-weekly-sync](skills/weibo-weekly-sync/README.md)
- [zhihu-weekly-sync](skills/zhihu-weekly-sync/README.md)

## 安装

将需要的 skill 文件夹放入客户端的 skills 目录，或在支持 GitHub 安装的客户端中指定本仓库及 `skills/<skill-name>` 路径。支持 OpenAI skill-installer 的环境可以使用：

```bash
python /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo GalgameCriticism/GalgameCriticism-skills \
  --path skills/weekly-cross-platform-sync
```

辅助脚本的依赖写在各 skill 的 SKILL.md 中。账号信息、Cookie 文件、下载的原文与运行记录保留在使用者本机，运行时传入。

## 增加技能

新建 `skills/<lowercase-hyphenated-name>/`，包含 `SKILL.md`（frontmatter 的 `name` / `description` 正确）与至少一句定位的 `README.md`，按实际需要添加 `scripts/`、`references/`、`agents/`；**同步更新上方技能目录**。其余约定（根 README 不放具体介绍、提交前脱敏自检、发布与浏览器行为）见 [AGENTS.md](AGENTS.md)。
