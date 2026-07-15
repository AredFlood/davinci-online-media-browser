# 安装指南

这份文档面向普通使用者，说明如何把插件安装到自己的 DaVinci Resolve。

## 从 GitHub 安装

```bash
git clone <本仓库地址>
cd davinci-online-media-browser
chmod +x install.sh
./install.sh
```

安装后请重启 DaVinci Resolve。

Studio 用户打开：

```text
Workspace -> Workflow Integrations -> Online Media Browser
```

免费版或浏览器模式打开：

```text
Workspace -> Scripts -> Utility -> Online Media Browser
```

## 从压缩包安装

```bash
tar -xzf davinci-online-media-browser-*.tar.gz
cd davinci-online-media-browser
./install.sh
```

首次打开会弹出 API Key 配置窗口。可以只填一部分，也可以先跳过。

## 安装位置

插件运行文件：

```text
~/.davinci_plugins/media_browser
```

本机配置文件：

```text
~/.davinci_plugins/api_keys.json
```

DaVinci Resolve Scripts 菜单入口：

```text
~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/Online Media Browser.py
```

DaVinci Resolve Studio 面板：

```text
/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/io.github.davincionlinemediabrowser.resolve
```

Studio 面板可能需要管理员权限写入系统目录。安装脚本会在需要时提示。

## 配置素材平台

| 平台 | 用途 | 获取地址 |
|---|---|---|
| Pexels | 图片、视频 | https://www.pexels.com/api/ |
| Pixabay | 图片、视频 | https://pixabay.com/api/docs/ |
| Freesound | 音效 | https://freesound.org/apiv2/apply/ |
| Mixkit | 音乐、音效 | 无需 Key |

如果不熟悉 API Key，先看 [API_KEYS.md](API_KEYS.md)。插件首次配置窗口里的“获取 API Key 教程”会打开本地教程页。

Key 只保存在你的电脑上，不会上传到项目服务器。

## 卸载

```bash
./uninstall.sh
```

同时删除 Key、设置和缓存：

```bash
./uninstall.sh --remove-user-data
```

## 常见问题

| 问题 | 处理 |
|---|---|
| Resolve 里没有菜单 | 完全退出并重新打开 Resolve |
| Studio 面板空白 | 重新运行 `./install.sh`，然后重启 Resolve |
| Scripts 菜单点了没反应 | 重新运行 `./install.sh`，确认 Python 可用后重启 Resolve |
| 证书或网络错误 | 运行 `./setup_local.sh` 安装证书依赖 |
| 可以下载但不能导入 | Studio 用户优先使用 Workflow Integration 面板入口 |
