# Separate Artifacts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 GitHub Actions 在一次构建中分别上传 Chrome 和 Chromium 两个独立 artifact。

**Architecture:** 保持现有双浏览器构建流程不变，只调整工作流中的上传步骤。每个浏览器目录各自对应一个 `upload-artifact` step，从而在 Actions 页面形成两个独立下载项。

**Tech Stack:** GitHub Actions、YAML、Python unittest

---

### Task 1: 拆分 artifact 上传步骤

**Files:**
- Modify: `.github/workflows/build.yml`

**Step 1: Write the failing test**

无需新增自动化测试；该任务属于工作流配置调整。

**Step 2: Write minimal implementation**

```yaml
- name: upload chrome
  uses: actions/upload-artifact@v4
  with:
    name: Chrome_${{ env.BUILD_NAME }}
    path: build/release/Chrome

- name: upload chromium
  uses: actions/upload-artifact@v4
  with:
    name: Chromium_${{ env.BUILD_NAME }}
    path: build/release/Chromium
```

**Step 3: Run verification**

Run: `python -m unittest tests.test_portable_build -v`
Expected: PASS

### Task 2: 同步使用说明

**Files:**
- Modify: `README.md`

**Step 1: Write minimal implementation**

补充说明 Actions 会生成两个独立 artifact，分别对应 Chrome 和 Chromium。

**Step 2: Run verification**

Run: `git diff --check`
Expected: PASS

### Task 3: 提交改动

**Files:**
- Modify: `.gitignore`
- Modify: `.github/workflows/build.yml`
- Modify: `README.md`

**Step 1: Stage relevant files**

```bash
git add .gitignore .github/workflows/build.yml README.md docs/plans/2026-04-08-separate-artifacts-design.md docs/plans/2026-04-08-separate-artifacts.md
```

**Step 2: Commit**

```bash
git commit -m "Separate Chrome and Chromium artifacts"
```
