# 验证结论

## 2026-05-25 Chrome + Chromium / Chrome++ command_line 改造验证

本轮先按 TDD 写入回归测试并确认红灯：

```bash
python -m unittest tests.test_portable_build -v
```

初始结果包含预期失败：缺少 `fetch_chromium_metadata`、`resolve_chromium_source_dir`，默认目标仍只有 Chrome，`build_release_name` 尚不接受 `chromium_revision`，`command_line` 尚未包含新增默认参数。

实现后已执行并通过：

```bash
python -m unittest tests.test_portable_build.SourceDirectoryTests -v
```

结果：

```text
Ran 2 tests in 0.005s
OK
```

这覆盖了 Chromium 解压后为 `payload/chrome-win` 目录，以及解压后直接为 `payload/chrome.exe` 扁平根目录两种情况。

已执行并通过：

```bash
python -m unittest tests.test_portable_build.ChromiumMetadataTests -v
```

结果：

```text
Ran 3 tests in 0.001s
OK
```

这覆盖了 Chromium `LAST_CHANGE` 正常 revision、空 revision 与非数字 revision。

已执行并通过：

```bash
python -m unittest tests.test_portable_build -v
```

结果：

```text
Ran 16 tests in 0.047s
OK
```

已执行并通过：

```bash
python -m py_compile portable_build.py run.py
```

结果：无输出，语法通过。

已执行并通过：

```bash
git diff --check
```

结果：无格式错误；仅有 Windows 本地 `LF will be replaced by CRLF` 提示。

已执行并通过 LSP：

```text
portable_build.py: No diagnostics found
tests/test_portable_build.py: No diagnostics found
README.md: No diagnostics found
```

已确认本地 `chrome++.ini` 非注释 `command_line`：

```text
command_line=--silent-debugger-extension-api --test-type --ignore-certificate-errors --no-first-run --no-default-browser-check
```

已搜索旧的单 Chrome 构建表述并通过，当前仓库代码/文档未再保留与双构建相冲突的旧说法。

结果：无输出。

已执行双目标主流程模拟测试，确认写出两个独立 artifact 名称：

```bash
python -m unittest tests.test_portable_build.MainFlowTests.test_main_extracts_chrome_and_chromium_and_writes_build_name -v
```

结果：

```text
Ran 1 test in 0.020s
OK
```

测试覆盖 `CHROME_ARTIFACT_NAME=Chrome_<version>_win64` 与 `CHROMIUM_ARTIFACT_NAME=Chromium_<revision>_win64`。

## 仍有效的历史验证

已验证 Chrome++ latest release 可解析：

```text
TAG=1.16.2
ASSET=Chrome++_v1.16.2_x86_x64_arm64.7z
SIZE=170404
DIGEST=sha256:9ae286bd9efaa8c7ddb791da8c4d2625c37aa14eb8c94821dc1bdfd85b85cc36
```

已确认本地 `version.dll`：

```text
Length         : 175616
FileVersion    : 1.16.2
ProductVersion : 1.16.2
```

## 验证限制

- 本地未运行完整 `python run.py` 端到端构建，因为：
  - 会真实下载大体积 Chrome/Chromium 包。
  - 仓库内 `7zzs` 是 Linux ELF，本地 Windows 不能直接执行。
- 完整端到端构建应由 GitHub Actions 的 Ubuntu runner 验证。
