# 点点数据页面获取研究

调查日期：2026-10-12。目标应用：王者荣耀，App Store ID `989673964`，点点 ID `492udu6wz9vvwij`，中国 `country=75`。

后续更新：美区工具榜调查已还原点点请求签名，但匿名请求仍返回 `201000 尚未登录`。最终使用 Apple 无需登录的 Top Grossing RSS 完成前 20 名网页，详见 [美区工具榜接口说明](us-utilities.md)。下文保留首次调查的验证结果。

## 已实现的结果

通过用户登录后的页面读取可见 DOM，保存为 `data/diandian-page.json`。Apple 的公开 Lookup 接口也实际返回了这款应用的数据，保存为 `data/apple-lookup.json`。`scripts/build_snapshot.py` 将两者整理为网页使用的 `data/snapshot.json`。

首版展示真实快照，未实现独立登录、批量采集、定时更新、完整点点功能复刻或精确趋势接口。网页数据无需点点登录即可在本机展示，但点点快照不会自动刷新。

| 数据 | 当前取得方式 | 实际获取结果 |
| --- | --- | --- |
| 应用基础信息、描述、截图、当前版本 | Apple Lookup | 已取得，可公开请求 |
| 分类排名、App 指数 | 点点登录后的页面 | 已取得页面快照 |
| 当前版本／所有版本评分及星级数量 | 点点登录后的页面 | 已取得，星级加总校验通过 |
| 10 项热门内购、10 条历史版本 | 点点登录后的页面 | 已取得页面快照 |
| 下载量、收入概览 | 点点登录后的页面 | 仅页面显示的 `>100万`、`>$1亿` 区间 |
| 精确下载／收入、排名与评分历史时间序列 | 独立接口 | 未取得 |
| 会员功能标签 | 当前账号显示升级提示 | 未取得 |

原页“全球速览”选中 **合集**，且两张概览卡选中“最近30天”。这些区间属于王者荣耀合集，不能标记为该单个 iOS 应用的精确数据。截图 `docs/diandian-source.jpg` 记录了选择状态和变化方向：下载下降 3.55%，收入上升 0.58%。页面没有明确说明变化比较基期，因此网页仅标注“原页展示变化”。中国份额分别为 84% 与 98%；其他地区为其余份额之和，未给出各国精确数量。

点点原页把 15,097,927 个评分标为当前版本、16,321,377 个评分标为所有版本；首版保留原页口径。Apple Lookup 的平均分为 3.24926，不能静默替换点点展示的 3.20。

## REA 的实际使用

已通过临时 `pnpm dlx rea-agents@latest` 运行 REA 6.4.0 CLI，未修改 Codex MCP 配置，未安装 Ghidra/Hopper。网页前端是 JavaScript，不需要原生二进制反编译。

从匿名 HTML 中发现并下载了 142 个公开脚本（约 14.1 MB），存放在 `/tmp/appstoredata-research`。执行：

```sh
pnpm dlx rea-agents@latest analyze-javascript-application /tmp/appstoredata-research --json > /tmp/appstoredata-rea-analysis.json
```

REA 完成全部 142 个文件的语法解析，报告 0 个解析失败。其应用关系图存在资源预算限制，不能声称完成所有运行时行为还原。仓库中的 `docs/rea-summary.json` 保留证据 ID、源摘要、统计、限制及关键脚本哈希；约 52 MB 的完整分析结果留在临时目录，不放进应用网页。

REA 的浏览器工作流需要一个已开启本地 CDP 调试端口的浏览器。当前会话使用 Codex 浏览器连接读取登录页面，并没有用 REA 捕获登录后的网络响应。静态分析和请求路径的定向源码检查已完成；“接口运行时采集完成”尚未成立。

## 发现的接口与阻碍

`app~f075b844.e803b6a.js` 中生产环境 API 基址为：

```text
https://api-d.diandian.com/pc
```

`app~f2cb6a90.523495b.js` 中请求拦截器将旧路径 `/web/api/` 转为 `/app/v1/`，`/web/api2/` 转为 `/app/v2/`，`/web/api3/` 转为 `/app/v3/`。

| 功能 | 前端路径 | 实际请求路径（相对于基址） | 已见参数 |
| --- | --- | --- | --- |
| 应用信息 | `/web/api/app/info` | `/app/v1/app/info` | `market_id`, `id`, `country_id`, `language_id`, `model_type` |
| 实时排名 | `/web/api/app/rank` | `/app/v1/app/rank` | `id`, `country_id`, `time`, `rank` |
| 排名趋势 | `/web/api/app/rank/trend` | `/app/v1/app/rank/trend` | `id`, `country_id`, `device_id`, `brand_id`, `start_time`, `end_time`, `time_type`, `rank_type`, `stat_type` |
| 下载趋势 | `/web/api2/stat/download/trend` | `/app/v2/stat/download/trend` | POST：`market_id`, `app_ids`, `start_time`, `end_time`, `device_id`, `country_id` |
| 收入趋势 | `/web/api2/stat/income/trend` | `/app/v2/stat/income/trend` | POST：`market_id`, `app_ids`, `start_time`, `end_time`, `device_id`, `country_id` |

本次对应用信息和实时排名做了直接请求验证，均为 HTTP 200，但响应业务失败：

```json
{"code":100009,"msg":"sign error"}
```

这不是取数成功。请求拦截器会按路径和 GET／POST 方式生成 `k` 参数，使用会话初始化的签名配置；请求还采用 `withCredentials`。仅复制接口 URL 不能保证调用成功，即使把公开签名逻辑恢复出来，也不能据此断言登录与会员权限已满足。

部分下载、收入、活跃等数据使用 `arraybuffer` 响应及 Protobuf `decode`／`toObject` 转换，需要对应 schema。是否能取得精确数据，要进一步在已登录、当前账号有权查看的页面记录实际请求与响应，分别验证签名、权限和解码。

关键位置：

- `app~daa4ffb1.f183724.js`：应用信息请求。
- `app~05e8810e.64c1621.js`：排名、排名趋势、下载趋势请求。
- `app~6ce0cfc9.94c687e.js`：收入趋势与 Protobuf 解码。
- `app~f2cb6a90.523495b.js`：Axios 拦截器、路径转换、签名 `L()`。
- `app~f075b844.e803b6a.js`：生产 API 配置。

## 下一步可选路径

1. **继续按当前账号可见页面采集**：已有真实数据，适合先验证展示和指标口径；依赖页面 DOM 和有效登录。
2. **抓取正常网络响应再接独立采集器**：用 REA CDP 观察或用户导出的 HAR，取得实际参数、响应结构和权限结果。需避免将 Cookie、token 或签名材料提交进仓库。尚未验证稳定性。
3. **点点官方 API**：页面顶部提供 API 服务入口，可进一步确认套餐、字段与授权方式。本次未申请或购买。
4. **Apple 公开数据源**：已经验证应用元数据能获取。它没有提供本次需要的第三方应用精确下载／收入数据，不能代替点点估算。

参考：[REA 浏览器指南](https://rea.tools/zh-CN/guides/browser/)、[REA 安装与 CLI](https://rea.tools/zh-CN/get-started/)、[Apple Lookup 响应](https://itunes.apple.com/lookup?id=989673964&country=cn)、[点点目标页](https://app.diandian.com/app/492udu6wz9vvwij/ios?market=1&country=75&id=989673964)。

## 2026-10-13 月下载、月收入专项实测

以 Cleanup（Apple ID 1510944943、点点 ID ygguvu6pgzr66c6）为样本，按美国 country_id=24、iOS market_id=1、2026-09 自然月发出无认证请求。复用公开脚本还原的 POST 签名算法，没有读取或导出浏览器 Cookie、token、用户凭据。

- `POST /pc/app/v2/stat/download/trend`：HTTP 200，业务 `201000：尚未登录`。
- `POST /pc/app/v2/stat/income/trend`：HTTP 200，业务 `201000：尚未登录`。
- 有效签名的榜单控制请求同样为 `201000`，不是 `100009 sign error`。参数、错误响应保存在 `data/diandian-monthly-api-check.json`，临时探测脚本为 `/tmp/appstoredata-monthly-probe.mjs`。尚未取得合法会话响应或完成月度 Protobuf 数据解码。
- 现有已登录免费账号的下载详情、收入详情和下载收入榜，都显示“当前为免费版，升级至专业版可查看更多数据”。收入页文本证据保存在 `data/diandian-monthly-page-check.json`。
- Cleanup 概览只有全球/合集“最近30天”的 `>100万` 下载、`>$100万` 收入范围与美国份额，不是美国单个 iOS 应用 2026-09 自然月精确值，未加入网页或月度均值。首页公开摘要属于中国地区，组件未明确统计年月，不用于美区工具榜。

已验证接口与签名，但当前免登录和免费账号条件不能采集目标月度数值。具备对应数据权限后，才可正常查询/导出并核对月份、国家、商店、货币和完整日覆盖，再扩展批量采集。本轮没有申请、购买或升级套餐。

## 2026-10-13 公开首页接口的新进展

对公开前端首页实际使用的 `GET https://api-d.diandian.com/pc/app/v1/index` 发出 `is_index=1` 的正常签名请求，无 Cookie、token 或账户凭据，实际返回 HTTP 200、`code=0`、`msg=success`。这与受保护的下载、收入趋势端点不同：公开首页确实能匿名取得部分月度摘要。

响应包含中国区（country_id=75）前 10 名下载榜和前 10 名收入榜，合计 18 个唯一 Apple ID，含原始整数 `downloads` / `incomes`。响应未明确统计年月和收入货币；其中 `calc_last=true` 不能单独证明绝对统计月份。当前美区工具榜精确匹配 0 个，因此没有填入其均值或新增空指标列。原始响应保存为 `data/diandian-public-index-check.json`，整理快照为 `data/diandian-public-snapshot.json`，临时可复现脚本为 `/tmp/appstoredata-public-index-probe.mjs`。

继续检索目标应用的公开点点摘要，没有取得美区工具应用的新增月度数值。Sensor Tower 新检索命中以 2025 季度的周度报告为主，未把周峰值、季度叙述或不同平台数字换算成上月值。
