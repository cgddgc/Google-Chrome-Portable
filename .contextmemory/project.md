# 项目概览

## 项目用途

本仓库用于自动下载官方 Chrome 离线包与 Chromium Win64 snapshot，并封装为 Windows x64 便携版。

核心目标：
- 程序输出为 `Chrome/` 与 `Chromium/` 目录。
- Chrome 主程序位于 `Chrome/App/chrome.exe`。
- Chromium 主程序位于 `Chromium/App/chrome.exe`。
- 用户数据分别位于 `Chrome/Data`、`Chromium/Data`。
- 缓存分别位于 `Chrome/Cache`、`Chromium/Cache`。
- 通过 Chrome++ 的 `version.dll` 和 `chrome++.ini` 实现便携化与标签增强。

## 技术栈与入口

- Python 3.10
- `requests`
- GitHub Actions
- `7zzs` 解压 Chrome 安装包、Chromium snapshot 与 Chrome++ 发布包

关键入口：
- `run.py`: 薄入口，调用 `portable_build.main()`。
- `portable_build.py`: 下载 Chrome、下载 Chromium snapshot、解析 Omaha 响应、准备 Chrome++ 文件、组装 portable 目录。
- `.github/workflows/build.yml`: CI 构建入口。
- `chrome++.ini`: Chrome++ 配置，当前为 UTF-16 编码的新版配置格式。
- `version.dll`: Chrome++ DLL，当前本地版本为 `1.16.2`。

## 长期约束

- 当前支持 Chrome Portable 与 Chromium Portable 双产物。
- GitHub Actions 可以构建时自动拉取 `Bush2021/chrome_plus` latest release 的 Chrome++ 主包。
- 本地构建默认使用仓库内的 `version.dll` 与 `chrome++.ini`，避免本地每次依赖网络。
- CI 构建使用 `CHROME_PLUS_SOURCE=latest python3 run.py`，从 latest release 抽取 `x64/App/version.dll` 和 `x64/App/chrome++.ini`。
- 构建时会对 Chrome++ 配置应用项目固定覆盖项，避免 upstream 默认值改变项目行为。
- Chrome 官方离线包解析为 `Chrome-bin`；Chromium Win64 snapshot 解析为 `chrome-win`。
- Chrome++ 的 `version.dll` 与 `chrome++.ini` 必须和最终 `chrome.exe` 位于同一目录，即 `Chrome/App` 或 `Chromium/App`。
- 默认 `command_line` 包含 `--no-first-run --no-default-browser-check`；不默认加入已移除/基本无效的 `--disable-infobars`。

## 关键目录

- `Chrome/App`: 构建后 Chrome 程序目录，含 `chrome.exe`、`version.dll`、`chrome++.ini`。
- `Chrome/Data`: Chrome 用户数据目录。
- `Chrome/Cache`: Chrome 缓存目录。
- `Chromium/App`: 构建后 Chromium 程序目录，含 `chrome.exe`、`version.dll`、`chrome++.ini`。
- `Chromium/Data`: Chromium 用户数据目录。
- `Chromium/Cache`: Chromium 缓存目录。
- `build/release/Chrome`: Chrome 构建输出目录。
- `build/release/Chromium`: Chromium 构建输出目录。
- `build/work`: 临时工作目录，构建结束应清理。

## 用户要求与协作约束

- 用户偏好直接落地，不喜欢无事实依据的猜测。
- 遇到外部依赖或兼容性问题必须主动查资料、给证据。
- 用户已明确本轮不要使用 Burp。
- 不要在未明确要求时 push。
