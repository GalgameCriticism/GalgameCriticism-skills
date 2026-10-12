# GalgameCriticism Skills

团队共用的 Agent Skills。每个 skill 独立放在 `skills/<skill-name>/` 下，工作流说明、辅助脚本和必要参考资料随 skill 一起维护。

## 技能目录

| Skill | 用途 |
| --- | --- |
| [bilibili-weekly-article](skills/bilibili-weekly-article/SKILL.md) | 把期目录 docx 文字稿与图包排版成 B 站图文（Opus），上传配图、生成预览供人工审核，存草稿或直接发布并回读；署名从飞书「周报工作表」按期号拉取 |
| [xiaoheihe-weekly-sync](skills/xiaoheihe-weekly-sync/SKILL.md) | 定位指定期号或最新 B 站周报，保留图文，按文章类型去重，核对小黑盒账号及社区后发布并回读 |
| [weibo-weekly-sync](skills/weibo-weekly-sync/SKILL.md) | 获取获授权微博周报，或将统一素材发布为微博头条文章，处理真实图片校验与失败恢复 |
| [zhihu-weekly-sync](skills/zhihu-weekly-sync/SKILL.md) | 连接独立会话，以嵌图 DOCX 发布知乎周报，核验全文和图片顺序 |
| [weekly-cross-platform-sync](skills/weekly-cross-platform-sync/SKILL.md) | 统一路由来源与目标平台，管理安装、账号核对、素材清单、去重和回执 |

## 标准生产链路

周报从原始素材到全平台分发分两段，中间以「人工审核并手动发布」为界：

```text
期目录（docx「去注音」稿 + 图包素材 + 封面）
      │
      ▼
┌───────────────────────────────────────────┐
│ bilibili-weekly-article（B 站图文生产端）  │
│  解析素材 → 飞书拉取署名 → 上传配图        │
│  → 本地预览 → 提交 B 站草稿                │
└───────────────────────────────────────────┘
      │  草稿箱（article_id 回执）
      ▼
   ✋ 人工审核：核对版式、配图与署名，
      在 B 站编辑器手动点击「发布」
      │
      ▼
   已发布的 B 站周报图文（cv 号 / 公开链接）
      │
      ▼
┌───────────────────────────────────────────┐
│ weekly-cross-platform-sync（跨平台编排）   │
│  按期号 / cv 号定位已发布图文，            │
│  采集一次不可变素材清单后分发              │
└───────────────────────────────────────────┘
      ├──▶ xiaoheihe-weekly-sync ──▶ 小黑盒
      ├──▶ zhihu-weekly-sync     ──▶ 知乎
      └──▶ weibo-weekly-sync     ──▶ 微博
```

三条约定：

1. **B 站是首发平台**：生产端只把周报做成 B 站草稿，「发布」由人工在审核后手动完成，技能不代发；
2. **搬运的输入是已发布的图文**：各平台 skill 从 B 站公开页读取内容，必须等 B 站发布完成后才能启动 `weekly-cross-platform-sync`；以发布回执和公开页为准，不重新解析本地素材；
3. **两段可独立使用**：只有 docx 和素材时用 `bilibili-weekly-article`；已有 B 站 cv 号时直接用对应搬运 skill，无需经过生产端。

## 安装

将需要的 skill 文件夹放入客户端的 skills 目录，或在支持 GitHub 安装的客户端中指定本仓库及 `skills/<skill-name>` 路径。支持 OpenAI skill-installer 的环境可以使用：

```bash
python /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo GalgameCriticism/GalgameCriticism-skills \
  --path skills/weekly-cross-platform-sync
```

完整链路见上方[标准生产链路](#标准生产链路)：`bilibili-weekly-article` 产出 B 站草稿，经人工审核发布后，`weekly-cross-platform-sync` 再按任务需要调用 `xiaoheihe-weekly-sync`、`weibo-weekly-sync`、`zhihu-weekly-sync` 和对应的目标发布适配器。也可以直接安装其中任意一个独立 skill。

辅助脚本的依赖写在各自的 SKILL.md 中。账号信息、Cookie 文件、下载的原文与运行记录保留在使用者本机，运行时传入。

## 增加技能

新建 `skills/<lowercase-hyphenated-name>/SKILL.md`，填写 `name` 和 `description`，按实际需要添加 `scripts/`、`references/`、`agents/`。在上面的技能目录添加一行，并验证 frontmatter、脚本和凭证脱敏。请勿将某位成员的用户名路径、令牌、Cookie、浏览器配置目录或运行产物提交到仓库。

工作流里涉及发布时，以用户授权的来源、账号和目标范围为准；说明发布前验证、结果核验和重复发布的处理方式。

发布完成后的最终回复必须直接提供每个成功平台的可点击公开文章链接；部分失败时也列出已成功链接及其余平台状态。浏览器优先连接独立会话；用户明确授权自动启动时可启动同一专用 profile，始终不重置或清理登录态。
