# 当前状态

## 目标

本轮目标：
1. 恢复 Chromium + Chrome++ 支持。
2. 评估并处理默认 `command_line` 增加 `--no-first-run --no-default-browser-check --disable-infobars` 的需求。
3. 保持 Chrome Portable 与 Chromium Portable 均输出为 `*/App/chrome.exe`，并确保 Chrome++ 文件与 `chrome.exe` 同目录。

## 现状

已完成代码、测试、工作流与文档改造，但尚未提交。

当前未提交改动包括：
- `portable_build.py`: 恢复双目标构建；新增 Chromium LAST_CHANGE 元数据获取、`chrome-win.zip` 下载模板、`chrome-win` 源目录解析；Chrome 与 Chromium 均输出到 `build/release/<Name>/App`，并复制 Chrome++ 文件。
- `tests/test_portable_build.py`: 更新为 16 个测试，覆盖 Chrome/Chromium 双目标、Chromium metadata、Chromium revision 数字校验、`chrome-win` 目录解析、Chromium 扁平解压目录 fallback、双目标主流程、Chrome++ 配置覆盖。
- `.github/workflows/build.yml`: job 名称为 `Warp_Browsers`，artifact 上传 `build/release/*`。
- `README.md`: 恢复 Chrome + Chromium 双产物说明。
- `docs/plans/2026-04-08-readme-release-clarification.md`: 修正旧计划中的单 Chrome 过时表述，避免与当前双构建状态冲突。
- `chrome++.ini`: 非注释 `command_line` 已更新为 `--silent-debugger-extension-api --test-type --ignore-certificate-errors --no-first-run --no-default-browser-check`。
- `.contextmemory/sessionhandoff.md`: 已消费并清空旧 handoff。

## 阻塞

无代码级阻塞。

注意：本地 Windows 无法直接运行仓库内 `7zzs`，因为它是 Linux ELF；完整端到端构建应在 Ubuntu/GitHub Actions 中验证。本地已用单元测试模拟解压路径和输出结构。

## 进展

已确认外部事实：
- Chromium Windows snapshot 通常解压为 `chrome-win` 扁平目录，`chrome.exe` 与主要 DLL/Pak 同根目录。
- Chrome 官方离线安装树与 Chromium snapshot 结构不同，当前代码分别处理：Chrome 取 `Chrome-bin`，Chromium 取 `chrome-win`。
- Chrome++ 要求 `version.dll` 与 `chrome.exe` 同目录，因此两个产物均把 Chrome++ 文件复制到 `App` 根。
- `--no-first-run` 与 `--no-default-browser-check` 仍是当前 Chromium/Chrome 支持的有效启动参数，适合便携包默认减少首次启动干扰。
- `--disable-infobars` 已移除/基本无效，不写入默认配置。

当前项目固定覆盖的 Chrome++ 配置：

```ini
data_dir=%app%\..\Data
cache_dir=%app%\..\Cache
command_line=--silent-debugger-extension-api --test-type --ignore-certificate-errors --no-first-run --no-default-browser-check
double_click_close=0
keep_last_tab=0
wheel_tab=1
wheel_tab_when_press_rbutton=1
```

## 下一步

1. 等待本轮后置审查子 agent 全部返回，处理任何必须修复的问题。
2. 如用户要求提交，先重新运行验证命令：
   - `python -m unittest tests.test_portable_build -v`
   - `python -m py_compile portable_build.py run.py`
   - `git diff --check`
   - 检查 `chrome++.ini` 非注释 `command_line`
3. 不要擅自 push。
