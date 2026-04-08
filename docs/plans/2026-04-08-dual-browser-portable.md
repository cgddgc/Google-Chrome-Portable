# Dual Browser Portable Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让一次构建同时产出 Chrome 和 Chromium 两个 Windows 便携版目录。

**Architecture:** 将下载、解压、目录整理、注入配置的核心逻辑提取到 `portable_build.py`，由 `run.py` 作为薄入口调用。Chrome 与 Chromium 通过不同的元数据获取方式进入同一套打包流程，最终写入统一的 `build/release` 目录。

**Tech Stack:** Python 3.10、requests、unittest、GitHub Actions

---

### Task 1: 建立可测试的失败用例

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_portable_build.py`
- Test: `tests/test_portable_build.py`

**Step 1: Write the failing test**

```python
class BuildTargetTests(unittest.TestCase):
    def test_default_targets_include_chrome_and_chromium(self):
        targets = portable_build.get_default_targets()
        self.assertEqual([target.output_name for target in targets], ["Chrome", "Chromium"])
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_portable_build -v`
Expected: FAIL with `ModuleNotFoundError` or missing function errors

**Step 3: Write minimal implementation**

```python
def get_default_targets():
    return [BuildTarget(output_name="Chrome"), BuildTarget(output_name="Chromium")]
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_portable_build -v`
Expected: PASS

### Task 2: 实现双目标构建核心逻辑

**Files:**
- Create: `portable_build.py`
- Modify: `run.py`
- Test: `tests/test_portable_build.py`

**Step 1: Write the failing test**

```python
def test_parse_chrome_update_response_returns_version_and_download_url(self):
    metadata = portable_build.parse_chrome_update_response(XML_SAMPLE)
    self.assertEqual(metadata.version, "135.0.7049.42")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_portable_build -v`
Expected: FAIL with missing parser/finalizer helpers

**Step 3: Write minimal implementation**

```python
def parse_chrome_update_response(xml_text):
    ...

def finalize_portable_directory(source_dir, release_root, output_name, injection_files):
    ...
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_portable_build -v`
Expected: PASS

### Task 3: 接入工作流与文档

**Files:**
- Modify: `.github/workflows/build.yml`
- Modify: `README.md`

**Step 1: Write the failing test**

无需新增自动化测试；以文档与 CI 行为变更为准。

**Step 2: Write minimal implementation**

```yaml
- run: python3 -m unittest tests.test_portable_build -v
- run: python3 run.py
```

**Step 3: Run verification**

Run: `python -m unittest tests.test_portable_build -v`
Expected: PASS

**Step 4: Commit**

按用户要求决定，本次默认不提交。
