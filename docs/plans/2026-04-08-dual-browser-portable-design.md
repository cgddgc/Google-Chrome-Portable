# 双浏览器便携构建设计

## 目标

一次执行构建流程时，同时产出 `Chrome` 和 `Chromium` 两个便携版目录，并保留现有 `version.dll`、`chrome++.ini` 注入能力。

## 范围

- 保留现有入口 `run.py`
- 新增可测试的构建逻辑模块
- 继续通过 GitHub Actions 一次执行完成双产物构建
- 更新 README 说明双浏览器产物

## 设计

1. 将实际构建逻辑收敛到 `portable_build.py`
2. `run.py` 仅保留入口职责，调用 `portable_build.main()`
3. Chrome 下载仍走 Omaha 接口，解析出版本号与安装包地址
4. Chromium 下载改走官方 snapshots：先取 `LAST_CHANGE`，再拼出 `chrome-win.zip`
5. 两个目标共用目录整理与注入逻辑，最终输出到 `build/release/Chrome` 与 `build/release/Chromium`
6. 构建名同时带上 Chrome 版本、Chromium 修订号和日期，便于回溯

## 风险与处理

1. 现有脚本通过 `shutil.move` 消耗注入文件，双目标构建下必须改为复制
2. Chromium 快照包的版本信息不稳定，构建名采用修订号而不是产品版本号
3. 当前仓库没有本地测试基线，需要补充最小单元测试并在工作流中显式执行
