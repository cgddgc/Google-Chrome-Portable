# 独立构建产物设计

## 目标

保持一次工作流同时构建 Chrome 和 Chromium，但在 GitHub Actions 页面分别输出两个独立 artifact，避免下载时混在一起。

## 设计

1. 保持 `run.py` 与 `portable_build.py` 的双目标构建逻辑不变。
2. 仅修改 `.github/workflows/build.yml` 的上传阶段。
3. 将原来的单个 `upload-artifact` 步骤拆成两个，分别上传：
   - `build/release/Chrome`
   - `build/release/Chromium`
4. artifact 名称分别带上浏览器名和 `BUILD_NAME`，便于区分。

## 风险与处理

1. 该改动不改变构建内容，只改变上传方式，回归风险低。
2. 若 `BUILD_NAME` 缺失，两个 artifact 仍会在步骤层面暴露问题，便于定位。
