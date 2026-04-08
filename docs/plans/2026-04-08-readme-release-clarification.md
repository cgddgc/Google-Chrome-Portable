# README Release Clarification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 README 清楚说明当前项目的“发布”其实是 GitHub Actions artifact，而不是 GitHub Release。

**Architecture:** 仅修改 `README.md` 的“获取”部分，补充 artifact 下载方式、nightly.link 作用与保留时间。构建脚本和工作流逻辑保持不变。

**Tech Stack:** Markdown、GitHub Actions

---

### Task 1: 澄清获取与发布说明

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

无需新增自动化测试；该任务为文档改写。

**Step 2: Write minimal implementation**

```md
项目当前不使用 GitHub Release。
README 中的“发布”实际是 GitHub Actions 构建并上传 artifact。
```

**Step 3: Run verification**

Run: `git diff --check`
Expected: PASS

### Task 2: 提交文档改动

**Files:**
- Modify: `README.md`
- Create: `docs/plans/2026-04-08-readme-release-clarification-design.md`
- Create: `docs/plans/2026-04-08-readme-release-clarification.md`

**Step 1: Stage relevant files**

```bash
git add README.md docs/plans/2026-04-08-readme-release-clarification-design.md docs/plans/2026-04-08-readme-release-clarification.md
```

**Step 2: Commit**

```bash
git commit -m "澄清构建产物下载说明"
```
