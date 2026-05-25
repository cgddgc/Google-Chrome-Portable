屠龙者终成恶龙，再见了Edge. 此项目在前人的肩膀上，加入了自己喜欢的定制。

# 功能

- ~~双击关闭标签页~~
- ~~保留最后标签页（防止关闭最后一个标签页时关闭浏览器，点X不行）~~
- 根据个人习惯取消了双击关闭，避免误触带来的麻烦
- 鼠标悬停标签栏滚动
- 按住右键时滚轮滚动标签栏
- ~~便携设计，程序放在App目录，数据放在Data目录（不兼容原版数据，可以重装系统换电脑不丢数据）~~
- 便携设计，Chrome 和 Chromium 程序分别放在 `Chrome\App` 与 `Chromium\App` 目录，数据和缓存分别放在同级 `Data` 与 `Cache` 目录，不会在 `%User%\AppData` 中建立目录（不兼容原版数据，可以重装系统换电脑不丢数据）
- 移除更新错误警告，移除不必要的显示（因为是绿色版没有自动更新功能）

以上配置都可以在chrome++.ini中进行修改.

# 获取

全自动无人管理项目，每周定时拉取最新 Chrome 离线包与 Chromium Win64 snapshot，并封装为便携版。

GitHub Actions 构建时会从 `Bush2021/chrome_plus` 的最新 GitHub Release 拉取 Chrome++ 主包，并使用其中的 x64 `version.dll` 与 `chrome++.ini`。仓库内也保留了一份当前可用的 Chrome++ 文件，供本地构建默认使用。

项目当前**不使用 GitHub Release**。这里的“发布”实际是指 GitHub Actions 自动构建并上传构建产物（artifact）。

下载入口：[https://nightly.link/zzp198/Google-Chrome-Portable/workflows/build/main](https://nightly.link/zzp198/Google-Chrome-Portable/workflows/build/main)

说明：

- GitHub Actions 每次会生成两个 artifact：`Chrome_<version>_win64` 与 `Chromium_<revision>_win64`，下载时分别对应两个 zip 文件
- 也可以直接到 GitHub 仓库的 `Actions` 页面进入对应 workflow 运行记录后下载 artifact
- `nightly.link` 只是对 workflow artifact 的下载代理，并不是单独维护的发布站点
- 当前 artifact 在 GitHub Actions 中默认保留 15 天

[![build status](https://github.com/zzp198/Google-Chrome-Portable/actions/workflows/build.yml/badge.svg)](https://github.com/zzp198/Google-Chrome-Portable/actions/workflows/build.yml)

# 安装

**解压 Chrome 或 Chromium 文件夹，为对应的 `App\chrome.exe` 建立桌面快捷方式即可**

# 更新

无法自动更新，未来可以建立独立的绿色升级软件。原 Chrome 每4周发布一次新版本，当前定时构建为每周，会出现最新版本与上次相同的情况，平时不需要频繁升级。

**保留 Chrome 或 Chromium 文件夹中的 Data 和 Cache，其他文件删除后解压新压缩包即可，单纯的文件替换。**

# 卸载

删除 Chrome 或 Chromium 文件夹，删除快捷方式即可，无残留。**注意提前保存 Data，避免自己的个人浏览数据清空（可谷歌账号同步，但不如 Data 全面）。**
