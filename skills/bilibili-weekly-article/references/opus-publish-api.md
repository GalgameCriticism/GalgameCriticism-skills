# B 站图文（Opus）发布接口

本技能发布端点与社区逆向成果（SocialSisterYi/bilibili-API-collect、Nemo2011/bilibili-api
issue #742/#137，2024~2026 多个独立实现一致）对齐，并用 cv53384810 的真实回读结构校验。

## 图片上传（发布前置）

```text
POST https://api.bilibili.com/x/dynamic/feed/draw/upload_bfs
Content-Type: multipart/form-data
字段: file_up=<图片二进制>, biz=new_dyn, category=daily, csrf=<bili_jct>
返回: data.image_url / data.image_width / data.image_height / data.img_size
      （字段在 data 内而非顶层；部分响应用 img_src/url，均兼容）
```

**必须走 `scripts/upload_bfs.py` 共享模块**（requests 直传）：120s 超时 + 每张最多
3 次尝试（退避 2s/4s）+ 顺序上传，264 期 42 张全成功。

⚠️ 库版 `bilibili_api.dynamic.upload_image` 走 aiohttp 且**不支持 timeout 参数**，
本机网络下 >1MB 配图稳定超时（2026-10-12 实测多数失败），仅作字段参考，勿直接依赖。
`build_opus.py`（直接发布）与 `save_draft.py`（草稿）均已切到共享模块。
上传失败即中止，不做静默跳过（防止图片丢失）。

## 创建图文

```text
POST https://api.bilibili.com/x/dynamic/feed/create/opus
Query: csrf=<bili_jct>, gaia_source=main_web, w_opus_req.upload_id=<upload_id>
      + wbi 签名（w_rid, wts）
Body(JSON):
{
  "raw_content": "<quill delta JSON 字符串>",
  "opus_req": {
    "upload_id": "<mid>_<unix_ts>_<4位随机数>",
    "opus": {
      "opus_source": 2,
      "title": "【Gal周报264期】…",
      "content": { "paragraphs": [ <para_type 1/2 段落，见 layout-spec.md> ] }
    }
  }
}
```

- `paragraphs` 即版面段落序列（文本段/图片段交替），与回读结构逐字段一致；
- `raw_content` 为 quill delta 版正文，`insert` 文本段与 `native-image` 图片段交替，
  尺寸单位字节（`size = KB * 1024`）；
- wbi 签名由 `bilibili_api.utils.network.Api(wbi=True)` 自动完成；
  `--no-wbi` 为接口免签名时的回退开关。
- 成功返回含 `dyn_id` / `dyn_id_str` / `dyn_rid`；公开页
  `https://www.bilibili.com/opus/<dyn_id_str>`（旧式 cv 页 `/read/cv<rid>/` 会跳转）。
- 已验证：错误凭证返回 `code=-101 账号未登录`，链路（签名/参数/JSON 体）可达。

## 文集（readlist）

- 已发布图文回读含 `basic.collection_id`（周报文集 = 471774）；
- 创建时是否收文集：社区实现未给出稳定参数。脚本提供实验性 `--collection <id>`
  （写入 `opus.collection_id`），发布后按回读 `collection_id` 判定是否生效；
  未生效时按回执提示走 创作中心→内容管理→专栏管理→选择文集 手动收录。
- 文集最新文章定位（跨平台复用时的来源校验）：
  `bilibili_api.article.ArticleList(471774).get_content()` 或 readlist 页面。

## 与 adoresever/bilibili-mcp 的关系（能力参考，非依赖）

<https://github.com/adoresever/bilibili-mcp>（2026-03，27 个工具）可作为登录与图片上传的
参考实现，但其发布工具不满足周报版面：

| 维度 | bilibili-mcp `bili_send_opus` | 本技能 create/opus |
| --- | --- | --- |
| 图文混排 | 否：`BuildDynamic` 的 contents 与 pics 分离，图片全部尾随正文 | 是：段落级交替 |
| 标题 | 拼进正文首行「【title】」 | 独立 `opus.title` |
| 封面 | 无 | 正文首图即横幅封面 |
| 图片上限 | 动态 9 张；opus 不截断 | 不截断 |
| 文集 | 无 | 实验性 collection_id + 手动收录指引 |
| 登录 | 二维码（base64/终端/URL） | 本技能 login_qr.py 终端二维码，凭证落 config.env |

结论：bilibili-mcp 适合「短图文动态」；周报长图文必须走 create/opus。
其 `bili_login.py` 的扫码流程与 `login_qr.py` 等价，可互相参考。

## 回读验证

```text
GET https://api.bilibili.com/x/polymer/web-dynamic/v1/opus/detail?id=<dyn_id>&features=itemOpusStyle
```

核对 `modules[].module_title.text` 与标题一致、`MODULE_TYPE_CONTENT.paragraphs` 中
`para_type=2` 的图片总数与发布数一致，并记录 `basic.collection_id`。

## 风险与边界

- wbi 签名参数与接口字段可能随 B 站调整；发布失败时先用 `--no-wbi` 排查，
  再对照创作中心手动发布，不反复重试（避免重复投稿）。
- 凭证仅存 `~/.config/bilibili-weekly-article/config.env`（600），
  不进仓库、不进命令行参数、不进日志。
- 发布幂等：发布前查 `_preview/publish_receipt.json`，已有成功回执则直接复用链接。
