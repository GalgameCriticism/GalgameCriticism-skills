# wechat-weekly-layout

独立将周报 Word 和图包排成公众号图文 HTML：封面、章节装饰、交替新闻卡、多图滑动或点击展开、往期推荐与 Staff；也可读取同一期微信文章复刻版式。

只需安装 `skills/wechat-weekly-layout`，无需安装其他平台技能。当前能力包含本地生成、预览和富文本复制，不包含登录公众号、自动上传图床或点击发表。

## 使用

安装 Python 依赖：`python3 -m pip install -r <skill>/requirements.txt`。然后让 agent 读取 [SKILL.md](SKILL.md)，并提供本期 Word、图包、封面及真实署名；素材结构见 [content-schema.md](references/content-schema.md)。

请求示例：

> 用 wechat-weekly-layout 把本目录的 Word 和图包排成公众号周报，保留多图交互，先给本地预览。

素材只有本地文件时可先 `render --local-only` 审稿；真实 HTTPS 图床 URL 写回后再生成公众号 HTML。预览通过本地 HTTP 服务打开，点击“复制公众号正文”后粘贴到公众号草稿。

## 宽度与编辑器检查

生成器将旧版 `160%～640%` 滑动轨道转换为宽度 `100%` 的 flex 图组；折叠改用 SVG `viewBox` 动画改变高度，展开时不增加宽度。检查文章内部元素，不依赖外层 `overflow:hidden` 遮盖溢出。

浏览器回归脚本可对生成稿检查手机／桌面宽度、图片、折叠和横向图组：

```bash
npm install --prefix <skill>/tests playwright
# 已安装 Playwright 浏览器时可省略；也可用 CHROME_PATH 指向本机 Chrome。
npx --prefix <skill>/tests playwright install chromium
node <skill>/tests/check-layout.mjs http://127.0.0.1:8765/output/article-local.html
```

本地浏览器、通用 contenteditable 粘贴、公众号后台保存回读和微信手机预览是不同验证阶段。未在实际公众号后台核验时，不能保证其过滤器完全保留 SVG；另提供折叠区展开版，以及把所有配图纵向展开的“兼容复制”／`wechat-safe.html` 作为备选。
