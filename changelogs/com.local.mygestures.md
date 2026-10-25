### 0.11.8 · 2026-09-13

- **修复「App 黑名单」只有微信生效**：根因是前台 App 判定优先走 `_accessibilityFrontMostApplication`，而该 API 在多数第三方 App 进程内返回 nil，导致除微信等少数 App 外黑名单恒判为未命中
- 改为直接取 `[NSBundle mainBundle] bundleIdentifier`：状态栏手势本就在前台 App 进程里跑，mainBundle 即 100% 可靠的前台 App，不再依赖脆弱的 SpringBoard 查询

### 0.11.7 · 2026-09-10

- **黑名单覆盖全 App**：前台 App 判定增加第二来源兜底（`SBSceneManagerCoordinator` 前台场景句柄），在 `_accessibilityFrontMostApplication` 拿不到时自动补位
- 「设置 → 我的手势 → App 黑名单」里拉黑哪个 App，进到那个 App 里状态栏手势即失效；桌面／SpringBoard 不受影响

### 0.11.6 · 2026-09-10

- **修复「App 黑名单」在第三方 App 内不生效**：此前依赖各 App 进程注入上报前台状态，部分越狱环境下第三方 App 未被注入，导致 SpringBoard 永远判断不到前台 App
- 改为纯 SpringBoard 侧直读前台 App，手势触发瞬间直接读当前前台 bundle id 再查黑名单
- 相机沿用上一版优化：走 `SBCameraHardwareButton` 预热路径，秒开
