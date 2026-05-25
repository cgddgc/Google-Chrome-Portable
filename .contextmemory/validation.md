# 验证结论

## 2026-05-25 Chrome + Chromium / Chrome++ command_line 与 Chromium artifact 版本号验证

本轮先按 TDD 写入回归测试并确认红灯：

```bash
python -m unittest tests.test_portable_build -v
```

初始结果包含预期失败：缺少 `fetch_chromium_metadata`、`resolve_chromium_source_dir`，默认目标仍只有 Chrome，`build_release_name` 尚不接受 `chromium_revision`，`command_line` 尚未包含新增默认参数。

后续针对 Chromium artifact 版本号补充红灯测试：

```bash
python -m unittest tests.test_portable_build.BuildNameTests -v
```

预期失败：`build_artifact_names()` 尚不接受 `chromium_product_version`。

```bash
python -m unittest tests.test_portable_build.WindowsVersionResourceTests tests.test_portable_build.MainFlowTests.test_main_extracts_chrome_and_chromium_and_writes_build_name -v
```

预期失败：尚未实现 `read_windows_product_version()`，主流程尚未把 Chromium 产品版本传入 artifact 名。

实现后已执行并通过：

```bash
python -m unittest tests.test_portable_build.WindowsVersionResourceTests tests.test_portable_build.BuildNameTests tests.test_portable_build.MainFlowTests.test_main_extracts_chrome_and_chromium_and_writes_build_name -v
```

结果：

```text
Ran 5 tests in 0.022s
OK
```

这覆盖了：
- 从 Windows `VS_VERSION_INFO` / `VS_FIXEDFILEINFO` 中读取 `ProductVersion`。
- 缺少版本资源时报错。
- Chromium artifact 名称写为 `Chromium_<product_version>_<revision>_win64`。

已执行并通过：

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

已执行并通过：

```bash
python -m unittest tests.test_portable_build -v
```

结果：

```text
Ran 19 tests in 0.055s
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

结果：无空白错误；仅有 Windows 本地 `LF will be replaced by CRLF` 提示。

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
