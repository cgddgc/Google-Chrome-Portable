# README 发布说明澄清设计

## 目标

澄清 README 中“自动编译发布”的含义，让使用者能区分 GitHub Actions artifact、nightly.link 下载入口与 GitHub Release。

## 设计

1. 不修改构建与上传逻辑，仅调整 `README.md` 的“获取”段落。
2. 明确说明当前项目不使用 GitHub Release。
3. 说明所谓“发布”实际是 GitHub Actions 构建后上传两个 artifact。
4. 说明 `nightly.link` 只是 workflow artifact 的下载代理入口。
5. 补充 artifact 名称、下载位置和保留时间，减少误解。

## 风险与处理

1. 本次仅为文档澄清，不影响构建逻辑。
2. 文案尽量贴合当前 workflow 配置，避免 README 与实际行为再次脱节。
