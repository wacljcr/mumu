# 常驻后台（wacljcr.keepalive）

### 1.0.5 · 2026-11-10

**新增功能：注销后自动拉起 + 设置面板简化。**

- **注销（respring）后自动拉起已保活 app** — 注销会重启 SpringBoard、杀掉所有 app 进程。现在注销完成后，系统会自动把**不在运行的已保活 app** 在**后台重新拉起**（不弹前台、不打扰你），拉起后仍保持常驻，重开不冷启动。
- **设置面板简化** — 面板精简为「一个总开关 + 允许被刷掉 + 要常驻的 app 列表」：
  - **总开关**：一键开启/关闭全部保活；
  - **允许被刷掉**：关（默认）= 保活 app 无法被一键清理/手动划掉刷掉；开 = 保活仍生效，但 app 可被刷掉（刷掉后重开需冷启动）；
  - **要常驻的 app**：9 个预置 app（微信/QQ/闲鱼/淘宝/京东/抖音/小红书/支付宝/微博）+ 「选择要管理的 App」可加任意 app（含巨魔/TrollStore 安装的）。

> 支持 iOS 15.0 – 16.6 的 rootless 越狱（Relaxin / RootHide / Dopamine），依赖 mobilesubstrate 或 ellekit、preferenceloader。

### 1.0.3 · 2026-11-08

**修复：被保活的 app（QQ / 微信等）通知声音消失。**

- **问题** — 装 1.0.2 后，QQ、微信等被保活 app 收到消息时**通知声音没了**。
- **原因** — 后台保活的「静音音频」用了 `AVAudioSessionCategoryPlayback`，该类别**默认独占音频路由**。被保活 app 在后台循环播放静音音频时，系统播放通知声音被这个独占会话阻断 → 通知没声音。
- **修复** — 给音频会话加 `AVAudioSessionCategoryOptionMixWithOthers`（混音）：保活音频不再独占音频路由，通知声音可以正常混入播放。
- **不影响保活** — 一键清理插件判断「正在播放媒体」靠的是 `MPNowPlayingInfoCenter`，与音频会话是否独占无关，所以保活效果不变（退后台仍常驻、清理不掉、重开不冷启动）。

> 支持 iOS 15.0 – 16.6 的 rootless 越狱（Relaxin / RootHide / Dopamine），依赖 mobilesubstrate 或 ellekit、preferenceloader。

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
