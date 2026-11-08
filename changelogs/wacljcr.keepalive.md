# 常驻后台（wacljcr.keepalive）

### 1.0.2 · 2026-11-08

**正式版：黑屏彻底修复 + 手动划掉也保住 + 支持巨魔应用 + 联系作者改复制QQ + 耗电可控 + 包名统一为 wacljcr.keepalive。**

- **黑屏彻底修复（核心）** — 之前 1.0.1 用「SpringBoard 侧挂起」解决黑屏，但 iOS 16 的 FBApplicationProcess 根本没有 `-suspend` 方法，挂起从未执行、实际退化成「直接拦杀」→ 进程活但场景被拆 → 重开仍黑屏。本版改为在**场景销毁之前**（`SBMainSwitcherControllerCoordinator._removeDisplayItem:forReason:` 系列）拦截对受保护 app 的终止，场景不拆、进程不死 → 一键清理 / 手动划掉都清不掉，且重开不黑屏
- **手动划掉也保住** — 之前多任务里手动划掉受保护 app 仍会被杀（冷启动、不黑屏）。本版在 SpringBoard 侧 hook 到手动划掉的真正上游（`_removeDisplayItem`），对受保护 app 直接放行不终止，划不掉、也不黑屏
- **自然常驻（底层保活）** — app 内运行时内存注入 `UIBackgroundModes=audio`（只改内存、不动磁盘文件，不触发腾讯系反篡改），配合静音音频 + jetsam 提优先级，系统不杀、一键清理插件跳过
- **QQ 长按面板正常** — 不再改写 App 本体 Info.plist，QQ / 微信长按消息面板不再被禁用
- **支持巨魔/TrollStore 应用** — App 选择器在系统枚举之外加文件系统扫描兜底，巨魔安装的应用也能勾选
- **联系作者改复制 QQ + 弹窗** — 点「联系作者」自动复制作者 QQ（1013182359）并弹窗提示，不再自动跳转 QQ
- **耗电可控** — 「音频保活」开关与后台优先级联动：关掉后 app 正常挂起、近乎零耗电；开启则常驻最稳、轻微后台耗电
- **包名统一** — 包名从 `com.wacljcr.keepalive` 改为 `wacljcr.keepalive`；偏好设置域不变，升级后设置保留；**安装前需先卸载旧包**（见详情页「安装注意」）

> 支持 iOS 15.0 – 16.6 的 rootless 越狱（Relaxin / RootHide / Dopamine），依赖 mobilesubstrate 或 ellekit、preferenceloader。
