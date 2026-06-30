# 达芬奇在线素材浏览器

一个给 DaVinci Resolve 使用的本地在线素材浏览器。你可以在插件面板里搜索 Pexels、Pixabay、Freesound、Mixkit 的素材，先预览，再下载并导入当前项目的 Media Pool。

本项目默认只在本机运行，不提供远程服务。API Key、下载缓存和设置都保存在你的电脑上。

## 主要功能

- 多源搜索：视频、图片、音乐、音效。
- 中文搜索：输入中文关键词后自动翻译为英文再检索。
- 面板内预览：图片、视频、音频都可以在插件页内预览。
- 后台下载：下载和导入时仍然可以继续搜索。
- 下载管理：查看下载进度、本地路径、项目名，并批量复制授权信息。
- 授权提醒：导入前提示授权风险，默认阻止非商用素材。
- 作者署名：保留来源、作者、授权链接和原始链接，方便项目交付时回溯。
- Studio 面板：DaVinci Resolve Studio 可通过 Workflow Integration 打开嵌入式面板。
- 免费版入口：免费版可通过 Scripts 菜单打开同一套浏览器界面。

## 支持的素材源

| 平台 | 内容 | 方式 |
|---|---|---|
| Pexels | 图片、视频 | 官方 API |
| Pixabay | 图片、视频 | 官方 API |
| Freesound | 音效 | API |
| Mixkit | 音乐、音效 | 免 Key 页面解析 |

Mixkit 和部分网页解析来源可能会受到网页结构变化或访问限制影响。Pexels、Pixabay 的官方 API 更稳定。

## 安装

```bash
git clone <本仓库地址>
cd davinci-online-media-browser
chmod +x install.sh
./install.sh
```

安装完成后，重启 DaVinci Resolve。

Studio 用户打开：

```text
Workspace -> Workflow Integrations -> Online Media Browser
```

免费版或浏览器模式打开：

```text
Workspace -> Scripts -> Utility -> Online Media Browser
```

如果只想安装 Scripts 菜单入口，不安装 Studio 面板：

```bash
./install.sh --no-wfi
```

## 配置 API Key

首次打开会出现“连接素材平台”窗口。可以只填写你需要的平台，也可以先跳过，之后从设置按钮重新打开。

| 平台 | 用途 | 获取地址 |
|---|---|---|
| Pexels | 图片、视频 | https://www.pexels.com/api/ |
| Pixabay | 图片、视频 | https://pixabay.com/api/docs/ |
| Freesound | 音效 | https://freesound.org/apiv2/apply/ |
| Mixkit | 音乐、音效 | 无需 Key |

你的 Key 保存在本机：

```text
~/.davinci_plugins/api_keys.json
```

仓库里只包含空模板 `api_keys.example.json`。

## 使用方式

1. 在搜索框输入关键词。
2. 选择素材类型和授权筛选。
3. 单击素材卡片，在右侧预览。
4. 满意后点击下载或导入到 Media Pool。
5. 如需整理授权信息，进入左侧下载管理页批量复制。

## 卸载

```bash
./uninstall.sh
```

默认保留 API Key、设置和缓存。彻底清理：

```bash
./uninstall.sh --remove-user-data
```

## 隐私与安全

- 本地服务只监听 `127.0.0.1`。
- API 请求需要随机令牌。
- API Key 不会上传到本项目服务器。
- 下载的素材仍受各平台授权条款约束，商用前请自行确认。

更多说明见 [SECURITY.md](SECURITY.md)。

## 已知限制

- DaVinci Resolve 没有公开 API 允许第三方把在线素材源直接放进原生 Media Pool。
- DaVinci Resolve 没有公开 API 允许把未导入的在线 URL 直接推到 Source Viewer。
- Workflow Integration 是 DaVinci Resolve Studio 功能，免费版只能通过 Scripts 菜单打开浏览器界面。
- Freesound 当前默认使用可预览音频，原始质量下载需要后续完善 OAuth 流程。

## 许可证

MIT。详见 [LICENSE](LICENSE)。

DaVinci Resolve 是 Blackmagic Design Pty Ltd. 的商标。本项目为独立项目，与 Blackmagic Design 无官方关联。
