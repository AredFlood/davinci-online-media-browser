# 新手获取 API Key 教程

这份教程给第一次接触 API 的用户使用。你不需要写代码，只需要注册素材平台账号，复制平台提供的一串 Key，然后粘贴到插件的“连接素材平台”窗口里。

## 先看这一张表

| 你想搜索什么 | 建议配置 | 插件里填写的位置 |
|---|---|---|
| 图片、视频 | Pexels、Pixabay | `Pexels API Key`、`Pixabay API Key` |
| 音效 | Freesound | `Freesound Client Secret` |
| 音乐、部分音效 | Mixkit | 不需要 Key，保持启用即可 |

可以只填一部分。比如你只想找视频，先填 Pexels 和 Pixabay 就可以；你只想找音效，先填 Freesound 就可以。

## 重要安全提醒

- API Key 相当于你的平台访问凭证，不要发到公开群、截图、GitHub 或视频里。
- 本插件会把 Key 保存在你电脑上的 `~/.davinci_plugins/api_keys.json`。
- 如果你怀疑 Key 泄露，请去对应平台重新生成或删除旧 Key。
- 复制 Key 时不要带空格、引号或中文标点。

## Pexels：获取图片和视频 Key

Pexels 用于搜索图片和视频。

1. 打开 Pexels API 页面：<https://www.pexels.com/api/>
2. 点击页面里的 `Get Started` 或进入文档页面。
3. 登录 Pexels 账号；没有账号就先注册一个免费账号。
4. 按页面提示申请 API Key。通常会要求你填写应用名称和用途，可以写：
   - 应用名称：`DaVinci Online Media Browser`
   - 用途：`Search stock photos and videos for local video editing workflow.`
5. 复制生成的 API Key。
6. 回到插件的 Key 配置窗口，把它粘贴到 `Pexels API Key`。
7. 点击保存。输入框变成就绪状态后，就可以用 Pexels 搜索图片和视频。

如果校验失败，请确认你复制的是完整 Key，并且 Pexels 账号已经登录成功。

## Pixabay：获取图片、视频和音乐 Key

Pixabay 用于搜索图片、视频，也可用于部分音乐来源。

1. 打开 Pixabay API 文档：<https://pixabay.com/api/docs/>
2. 登录 Pixabay 账号；没有账号就先注册一个免费账号。
3. 登录后，文档页面会显示你的个人 API Key，通常在 `key` 参数附近。
4. 复制完整 Key。Pixabay Key 常见格式类似 `12345678-xxxxxxxxxxxxxxxxxxxxxxxx`。
5. 回到插件的 Key 配置窗口，把它粘贴到 `Pixabay API Key`。
6. 点击保存并等待校验。

如果看不到 Key，先刷新 API 文档页面，或确认你已经登录 Pixabay。

## Freesound：获取音效 Key

Freesound 用于搜索音效。当前插件默认使用可预览音频；完整质量下载需要后续 OAuth 流程完善。

新手优先填写 `Client Secret / API Key`，一般不需要先处理 OAuth。

1. 打开 Freesound API 凭证页面：<https://freesound.org/apiv2/apply/>
2. 登录 Freesound 账号；没有账号就先注册一个免费账号。
3. 申请新的 API 凭证。页面如果要求填写应用信息，可以参考：
   - Name：`DaVinci Online Media Browser`
   - Description：`Search sound effects for local DaVinci Resolve projects.`
   - Website：可以填项目主页，或临时填 `http://localhost`
   - Redirect URI：如果页面要求填写，可填 `http://localhost`
4. 提交后，你会看到一组凭证。
5. 复制 `Client Secret / API Key` 这一栏的长字符串。
6. 回到插件，把它粘贴到 `Freesound Client Secret`。
7. `Client ID` 可以一起填，也可以先不填；当前搜索音效主要依赖 `Client Secret / API Key`。
8. `OAuth Token` 可以先不填。它主要为将来完整质量下载准备。
9. 点击保存并等待校验。

如果校验失败，优先检查你是否把 `Client ID` 误粘到了 `Client Secret` 输入框。搜索音效需要的是 `Client Secret / API Key`。

## Mixkit：无需 Key

Mixkit 不需要 API Key。插件配置窗口里保持 `启用 Mixkit` 即可。

注意：Mixkit 属于网页来源，偶尔会受到网页结构变化、地区网络或访问限制影响。如果它临时不可用，优先使用 Pexels、Pixabay、Freesound 这些官方 API 来源。

## 在插件里保存

1. 打开 DaVinci Resolve。
2. 打开插件：
   - Studio：`Workspace -> Workflow Integrations -> Online Media Browser`
   - 免费版或浏览器模式：`Workspace -> Scripts -> Utility -> Online Media Browser`
3. 第一次打开会自动弹出 Key 配置窗口。
4. 把你拿到的 Key 粘贴到对应输入框。
5. 点击 `保存`。
6. 成功后会出现连接成功提示；失败时，插件会标出有问题的平台。

## 常见问题

### 可以一个 Key 都不填吗？

可以。你仍然可以保留 Mixkit，但 Pexels、Pixabay、Freesound 对应的搜索结果会不可用或减少。

### 为什么 Key 明明填了还是校验失败？

常见原因：

- 多复制了空格、换行或引号。
- 把 Freesound 的 `Client ID` 填到了 `Client Secret`。
- 平台网页还没有完成申请流程。
- 当前网络无法访问对应平台 API。
- macOS 或 DaVinci 自带 Python 的证书过旧。可以运行 `./setup_local.sh` 安装证书依赖。

### 我填错了怎么办？

点击插件左侧的设置按钮，重新打开 Key 配置窗口，修改后保存即可。也可以勾选删除某个平台的 Key。

### 如何确认 Key 没有被上传？

插件只在本机启动服务，配置文件默认在：

```text
~/.davinci_plugins/api_keys.json
```

仓库里只有 `api_keys.example.json` 空模板，不应该提交你的真实 `api_keys.json`。

