### 2.3.53 · 2026-10-27

- **修复「开了通知却不显示 / 开关像假的」排查**：通知身份解析 `NTM_sectionOf` 改为多重兜底——直接 `sectionIdentifier` 失效时，再尝试 `bulletin.sectionID` / `content.sectionIdentifier`，避免通知的 section 与你在面板里配置的 bundleId 对不上、导致开关实际控制的是另一把锁
- **新增诊断日志**：`postNotificationWithRequest:` 每次派发时在 SpringBoard 记录真实 section 与总开关判定（PASS/DROP），可在面板的诊断日志里确认某 App 的通知到底被哪一层拦了（最多保留 50 条）

### 2.3.52 · 2026-10-26

- **系统应用去噪（白名单化）**：「系统应用」分类由全量 147 收敛为白名单 + 系统通知登记两项并集——只显示策划白名单内、或已在系统通知中心登记过的系统应用，过滤掉 100+ 系统守护进程/扩展/隐藏工具等无开关可管的噪音项
- **白名单 36 个常用系统应用**：含 Safari浏览器/信息/FaceTime/照片/指南针/相机/App Store 及备忘录/播客/地图/天气/健康等（测距仪 com.apple.measure、放大器 com.apple.Magnifier 用正确 Bundle ID），Safari/相机/指南针等未登记但需被控的已显式纳入
- 网络/蜂窝策略、通知维度对列出的系统应用照常生效；那些无开关可管的扩展/守护继续不列

### 2.3.51 · 2026-10-26

- **系统应用补全与可见性修复**：放开 NTM_hasNotifications 过滤，Safari/相机/指南针等未在系统通知中心登记的系统应用此前被挡掉、面板看不到也无法管理（抹除/还原设置后断网只能在系统蜂窝救回）；现 /Applications 下所有 com.apple.* 系统应用均显示并可管理（通知维度无则忽略，网络/蜂窝策略照常生效）
- **IPA 端白名单修正**：修正两处错误 Bundle ID——测距仪 com.apple.measurify 改为 com.apple.measure、放大器 com.apple.magnifier 改为 com.apple.Magnifier；并新增 Safari浏览器/信息/FaceTime/照片/指南针/相机/App Store 共 7 个系统应用白名单

### 2.3.49 · 2026-10-25

- **支持 iOS 14**：最低系统降到 14.0，并新增 rootful 包 —— iOS 14 请装 rootful 版，iOS 15 及以上装 rootless 版
- 构建最低版本号写进二进制的 LC_BUILD_VERSION，避免在 iOS 14 被 dyld 直接拒绝加载

### 2.3.46 · 2026-10-25

- **修正「系统应用」虚高**：识别 Info.plist 里 SBAppTags 含 hidden 的后台服务（这正是 SpringBoard 判定「不上主屏」的机制），沙盒读不到 plist 时按系统版本分流兜底
- **Safari 不再重复出现**：只认顶层 .app，排除嵌套包

### 2.3.0 · 2026-08-26

- **增强开关**（每个 App 独立）：仅隐藏角标 / 隐藏通知预览（隐私）/ 切后台自动断网
- **关键词过滤**：按 App 编辑关键词黑名单，命中即拦截该条通知
- **应用分组**：给 App 打标签，整组一键开启 / 关闭 / 断网
- **模式快照**：一键保存全部配置，随时回滚
- **拦截日志**：记录被拦截的通知与断网事件
- **反馈**：设置页右上角「反馈」，一键发邮件并自动附带机型与系统版本
