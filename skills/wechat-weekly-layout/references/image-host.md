# 自建 Zipline 图床导出

此模式只上传用户授权的配图到用户指定图床；不会创建或发表微信公众号文章。
图床需提供可匿名读取、无过期签名的 HTTPS 原图直链；上传和图库管理需登录。
不要给原图配置会阻止微信抓取的 Referer 白名单、登录页或交互验证码。

## 准备

用户先提供本期文稿、图包、封面、图床地址和登录方式、推荐阅读的周报/留言板链接、Staff。
按 SKILL.md 完成素材映射和本地 render。默认发布副本单张 ≤500 KiB（512000 字节）：普通静态图转 JPG，正文透明图合成白底，宽度最多 1600 px。上传脚本在联网及读取凭证前重新检查/处理同一策略，已达标的 JPG 不重复有损编码；旧模板必须先用当前 skill 重新 render。
透明装饰以 `assets[].role` 标记并保留原格式，动画保持原字节，超限时停止。用户明确要求保留原图时，render 和上传命令均需独立指定 `--original-images`，此时不保证 500 KiB 上限。处理后的字节改变会生成新哈希，不复用旧图片直链。

Zipline 管理员在后台创建普通编辑账号或邀请成员，为其生成 API Token。
成员可以使用独立账号，或按团队约定共用普通账号的 Token；共用账号意味着共享图库及该账号的修改/删除权限。
管理员凭证不用于日常排版。实际凭证通过安全渠道分发，放环境变量、系统钥匙串或权限 600 的本机文件。

## 执行

脚本参数全部运行时提供，不把真实服务配置写回 skill：

```bash
python3 <skill>/scripts/zipline_images.py \
  --preview <project>/output/preview.html \
  --api-base 'https://<图床域名>' \
  --public-base 'https://<图床域名>' \
  --folder '周报-<期号>' \
  --token-env ZIPLINE_TOKEN
```

`ZIPLINE_TOKEN` 由用户或凭证管理器注入，不把值写在命令中。
也可用 `--keychain '<服务名>/<条目名>'` 或 `--token-file '<本机私密文件>'` 替代 `--token-env`。
内网上传可显式指定 `--api-base 'http://<私网IP>:<端口>'`，`--public-base` 仍必须是公网 HTTPS origin。
不要使用网页登录密码代替 API Token；Zipline Authorization 使用 Token 原值，无 Bearer 前缀。

默认缓存为输出目录 `image-host-map.json`；可用 `--cache` 指定跨期共用缓存。
缓存按图床地址和账号隔离，含文件哈希、图片地址及文件 ID，不含登录凭证。
每次复用前都以无 Cookie、无 Token 的请求核对图片 MIME、长度和 SHA-256。
对于上传超时，先核验由账号/内容哈希确定的预期地址，再决定是否重试，最多三次。
遇到 HTTP 429 时按 `Retry-After` 等待（单次至多 60 秒），仍受三次尝试上限约束。

## 产物与验收

- `preview.html`：离线原版。
- `preview-hosted.html`：视觉预览仍有本地图片；复制时改用 HTTPS 直链，需要联网粘贴到微信。
- `wechat-hosted.html`：保留交互的正文。
- `wechat-expanded-hosted.html`：展开折叠区的正文。
- `wechat-safe-hosted.html`：全部配图纵向展开的正文。
- `image-host-map.json`：续传与去重记录，不随技能提交。
- `image-host-verification.json`：匿名字节核验结果，不能替代微信后台验收。

复制图床版后读取剪贴板，确认图片全部为目标图床 HTTPS 地址、无 Base64 或 Token。
粘贴到微信，等待图片处理、保存草稿、重新打开，并核对图片数量、末图、折叠/横滑和手机预览。
只有完成这些步骤，才能标记微信编辑器验收通过；遇到失败列出实际失败图片及状态。
