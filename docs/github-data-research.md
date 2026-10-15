# GitHub 下载／收入数据方法调查

核对时间：2026-10-12。目标是美国区 iOS 竞品下载量、收入、上个自然月及历史累计。只读检索与源码核对；没有安装或运行第三方仓库，也没有使用网站登录 Cookie、泄露的账号或 API token。

## 可用于数据接入的项目

| 项目 | 源码／文档确认的能力 | 获取条件与验证边界 |
|---|---|---|
| [appfigures/cli](https://github.com/appfigures/cli) | 官方 CLI/MCP；`metrics query estimates.sales`、`estimates.revenue`；支持 country、start/end、按月及 `--all-time` | 需要 Appfigures 认证和 Public Data API 权限／credits；本次未用授权账号测试数据响应 |
| [econosopher/sensortowerR](https://github.com/econosopher/sensortowerR/blob/main/R/metrics.R) | 批量 App ID、国家、日期、日／周／月／季度；实际调用 `{os}/sales_report_estimates`；iOS 下载合并 `iu+au`，收入合并 `ir+ar` 并由美分转 USD | 需要 Sensor Tower API token；实际匿名请求该收入端点返回 HTTP 401 |
| [muzerow/rappmagic](https://github.com/muzerow/rappmagic/blob/master/R/am_history_apps.r) | `GET https://api.appmagic.rocks/v1/history/application`；App ID、商店、国家、日期与聚合参数；CSV | `Authorization` 必填；`am_auth` 生成账户 Basic 认证；源码注释最早日期为 2015-01-01；当前官方 docs 无法读取，未确认旧接口仍可用 |
| [LevenWin/diandian_app](https://github.com/LevenWin/diandian_app) | Playwright 监听页面响应、分页、持久化 profile、本地 dashboard；升降榜及关键词增长榜 | README 明确要求微信扫码；依赖网页自动生成签名，未反编译签名；未实现竞品下载／收入时间序列；公开仓库但 README 明确未提供开源协议 |
| [facundoolano/app-store-scraper](https://github.com/facundoolano/app-store-scraper) | iTunes/App Store 信息、榜单、评分、评论、版本等 | 文档列出的采集方法不提供竞品销量／收入；适合补充现有 Apple 元数据采集 |

Appfigures 的 [官方访问说明](https://help.appfigures.com/en/article/appfigures-api-cli-and-mcp-access-limits-and-public-data-1seiibo/) 明确：竞品数据需要 Public Data API add-on，API、CLI、MCP 共用额度；每日请求限额与竞品数据 credits 是不同概念，不能把“每日 1,000 请求”当成“免费读取 1,000 次竞品收入”。当前文档未在所读表中给出下载／收入请求的明确 credits 价格。

## 免费自行估算的方法

- [ree1ezixxx/open-source-app-kittie](https://github.com/ree1ezixxx/open-source-app-kittie/blob/main/packages/intelligence/src/revenue.ts)：收入以评分／评论总量的 0.85 次幂为基础，再乘分类系数、评分、评论增长、内购数量、广告数量和排名修正；下载量又从收入除以预设 ARPU 推导。没有在这段模型代码中发现以实际销量校准的证据。属于自建启发式估值，不是抓到的竞品销量。不能据此填成真实第三方历史累计。
- [Audie-glitch/rankrange](https://github.com/Audie-glitch/rankrange)：用户自己给 rank-to-downloads 曲线和收入／下载假设，支持不确定范围。README 明确没有实时网络取数，也不会读取 Sensor Tower 数据；适合作为透明估算实验，而非原始数据接口。

## 排除的线索

- [lorainemg/sensortower-scraper 的 parse_response](https://github.com/lorainemg/sensortower-scraper/blob/main/scraper.py) 把 `rating_count` 写入 `downloads` 字段。其“下载量”实际是评分数量，不能采用；所带 iOS US 文件只有 2020-08-29 的空内容。
- [Y34bsira/sensortower-scraper](https://github.com/Y34bsira/sensortower-scraper) 只提取 Top Free 的排名、应用和开发者，没有实际下载次数／收入金额。
- `vivgao/Sensortower-Script` 是旧 Selenium 网页方案，源码登录函数依赖硬编码账户，未使用；不能视为免认证 API。
- 搜索索引中的 `skiffer/getappniche-examples` 声称使用 Bearer API Key，但本次 GitHub 当前文件读取返回 404，因此不作为已核实可用项目。

## 实际匿名端点探测

```text
GET https://api.sensortower.com/v1/ios/sales_report_estimates
app_ids=1510944943
countries=US
date_granularity=monthly
start_date=2026-09-01
end_date=2026-09-30
无 auth_token、Authorization 或 Cookie
HTTP 401
{"error":"You need to sign in or sign up before continuing."}
```

该结果证实端点存在并要求认证，不代表授权后已取得这 20 个应用的数据。

## 适合当前网页的接入路线

优先研究 Appfigures：用专用后端 API Key 查询 `estimates.sales` 和 `estimates.revenue`，指定美国、iOS、2026-09-01 至 2026-09-30。Appfigures 的产品 ID／unified ID 与 Apple trackId 不一定相同，须先通过 lookup/search 建立精确对应关系。

历史累计需要先核对每个应用的最早可用数据日期、上架日期和权限范围，再对有效期间加总；`--all-time` 只表示 API 可用全部历史，不保证覆盖应用自上架以来所有时间。缺失日不能填 0。

在不取得任何数据服务授权的情况下，可继续收集公开摘要并从现在起保存历史快照，但本次未找到经实测可用的、完全免费免认证且能返回美国区竞品完整下载／收入历史的开源接口。当前网页的 IOSMRR/Sensor Tower 数据仍是各自公开快照。

## 2026-10-13 AppMagic / AppTweak 核查

- AppMagic：实际打开 [Cleanup 应用页](https://appmagic.rocks/iphone/cleanup-phone-storage-cleaner/1510944943)，下载量与收入均显示“登录以解锁”。根据 rappmagic 现有源码向 `/v1/history/application` 发出无认证的 2026-09 月度请求，返回 HTTP 401：`unauthenticated for invalid credentials`。旧文档入口未能读取，尚未验证授权后的参数兼容性和数据权限。本轮未取得估算值。
- AppTweak：官方 [Starter 定价](https://www.apptweak.com/en/pricing) 和 [免费估算介绍](https://www.apptweak.com/en/aso-blog/free-app-download-and-revenue-estimates-now-in-apptweak) 说明 Market Intelligence Starter 提供免费上月下载及收入摘要。其 [免费注册入口](https://app.apptweak.com/accounts/new?locale=en&plan_code=mi-starter2510&product=market_intelligence&recurrence=1year) 与一般 ASO 7 天试用入口不同；仍须用户创建或登录账号后实测网页数据及批量可用性。
- AppTweak API 是单独的积分权限，不能由免费网页计划推断免费 API 权限。[App Metrics 文档](https://developers.apptweak.com/reference/app-metrics) 要求 `x-apptweak-key`，Current 为日值，History 为指定日期区间的日序列，不能把 Current 日下载直接标为月下载。本轮无 token 请求 Cleanup 的 Current 下载和收入端点，返回 HTTP 401 `UnknownTokenError`，消耗 0 积分。
- [API FAQ](https://help.apptweak.com/en/articles/6051232-faq-app-store-api) 提供 7 天、20,000 积分试用；完整 30 日、200 应用、下载和收入双指标按现行历史接口费率估计需 780,000 个数据积分，另有请求费，不能声称试用额度可覆盖全部榜单。优先验证免费网页摘要；本轮未启用试用或付费套餐，也未将未取得的数据加入网页或均值。

### 不登录路径的进一步实测

用户要求两家都不要登录。没有使用 Appfigures 凭据、浏览器账户 Cookie 或第三方密钥来访问这两家。

- AppMagic [DEEP FLOW 公开发行商页](https://appmagic.rocks/publisher/deep-flow-software-services/2_1833881740) 的匿名表格确实可读取应用列表和**累计范围**：Cleanup 对应 Apple ID 1510944943，累计收入 `> $200,000,000`、累计下载 `> 100,000,000`。截图核对其时间列为“上线至今”，包含 iPhone/iPad 和 Google Play 关联应用；并非美国区上个月值。近 30 天两个切换入口的公开 DOM 均标记为 `period-btn ... lock`；没有尝试解除锁定。
- AppMagic 应用页的下载／收入小部件和旧历史 API 仍要求认证。尝试下载当前页面公开引用的 Angular 主脚本以研究匿名入口，服务器返回 HTTP 403，未规避挑战。浏览器资产导出仅支持媒体／字体／样式，不能导出脚本。本轮没有发现可用的匿名月度接口。
- AppTweak 匿名访问 `https://app.apptweak.com` 实际重定向到 `/users/sign_in`。登录页 HTTP HTML 未包含 downloads、revenues 或 market_intelligence 数据。其公开[生产力与工具报告](https://www.apptweak.com/en/reports/most-downloaded-productivity-tools-apps) 有 2025 全年、全球双商店的下载统计，不能除以 12 当成当前上月，也未混入榜单均值。
- 当前结论：无需登录可获取一部分元数据、累计范围和公开报告；**两家当前上月下载／收入没有取得**。未向网页新增空来源列，未新增历史累计列，未把累计、年度、阈值数据当作月度精确点估算。

## 2026-10-13 七麦匿名公开数据

实际打开美国区 Cleanup 的[下载量页面](https://www.qimai.cn/app/download/appid/1510944943/country/us)和[收入页面](https://www.qimai.cn/app/income/appid/1510944943/country/us)，页面仍有登录入口，未登录、未使用 Cookie 导出或第三方仓库中的登录凭据。两页公共应用头部显示 Apple App ID `1510944943`、美国地区、昨日下载预估 `23,742`，同时可以看到评分、版本与上架信息。

下载趋势和收入主体显示“登录/注册后可查看更多数据”，没有读取到月度下载合计或收入值。昨日标签未另标绝对统计日期。公开数值与口径保存在 `data/qimai-public-sample.json`，截图为 `docs/qimai-public-yesterday.jpg`；没有将单日乘 30、没有填入月度均值，也尚未声称已验证自动采集 API。

GitHub 上旧七麦爬虫使用 analysis 请求签名，部分仓库硬编码登录 Cookie。后者不能作为匿名获取成功的依据，未采用其凭据。公开页 HTTP 直接读取只取得约 2.9 KB 的前置响应，未包含估算值；本轮取得的数字来自实际浏览器可见页面。

## 2026-10-13 批量公开采集结果

- 七麦：逐个打开 Top 200 的 `/app/download/appid/{AppleID}/country/us`，等候公开头部加载，从 `.app-info .i-id .new-value` 核对 ID、`.logo-wrap .i-country .ivu-dropdown-rel` 核对美国、`昨日下载量` 对应的 `.value` 采集原页数字。未登录、未导出或注入 Cookie、未运行第三方签名代码。200 个均检查，首次缺失 8 个经复核补到 199 个；89 个大于零，110 个显示零，Calmia ID 6760277293 两次未成功加载。零只代表网页显示值，不保证真实零下载。每行保存采集时间和来源 URL，绝对统计日期未核实。
- `data/qimai-public-snapshot.json` 接入现有表格最后一列，标题“七麦 · 昨日下载 / 美国 iOS · 日预估”，保持 K/M/B，零注明“原页显示 0”，缺失为“未获取”。不参与月度均值。刷新按钮仍只更新 Apple，未实现自动日采集/API。
- AppMagic：实际采集 DEEP FLOW、GM UniverseApps、NordVPN 三个发行商的匿名表格。共保存 46 个具有明确 Apple ID 的应用累计范围，当前榜单精确覆盖 Cleanup、Cleaner Guru、NordVPN 三个；其余为同发行商其他应用。保存在 `data/appmagic-public-snapshot.json`。有的发行商只公开下载范围，收入缺失，不能补零；不同商店的关联组未拆分。近 30 天锁定，不恢复用户移除的历史累计列。
- AppTweak：匿名 HTTP 获取官方生产力与工具报告表格 10 行，保存在 `data/apptweak-public-report.json`；2025 全年、全球、App Store 与 Google Play 合并，报告无 Apple ID，不模糊映射当前榜单，不除以 12，不参与月度均值。
- 再次无认证实测 AppTweak Current 和 AppMagic history 两个已核实端点，均返回 HTTP 401，响应记录于 `data/public-provider-api-checks.json`。没有月度数据可加入这两家来源列。公开快照下载链接位于现有卡片的来源说明中。
- 验证：18 项 Python 单元测试通过，新增测试核对七麦按 ID 关联、日度值不改变月度均值、未知 ID 不继承数据；JavaScript 语法检查通过。

最终刷新验证：Apple 榜单换入 8 个新应用，按精确 ID 发现七麦覆盖从 199 降到 191。补采新上榜 8 个及原未加载 Calmia 后，共保存 208 个唯一 App ID，当前 200 名全部匹配，93 个大于零、107 个原页显示零；没有未匹配项。网页 200 行，每行 16 列，Cleanup 七麦 23.74K，前方月均值仍为 3.33M / $12.33M。底部横向滚动条与表格滚动同步，截图 `docs/us-utilities-qimai-public.jpg`。榜单变化后覆盖数动态计算，不按旧名次套值。

## 2026-10-13 公开来源继续扩展

- 点点：首页接口无需登录可成功返回中国区前 10 下载榜与前 10 收入榜，18 个唯一 Apple ID。统计年月、收入单位未核实，当前美区工具榜匹配 0 个；快照链接放在已有卡片的来源说明中。目标应用趋势端点仍要求授权，未继续探测受保护数据。
- IOSMRR：公开 HTML 显示 `DATA · SEP 2026`，支持 `q` 搜索、分类和分页，每行有 Apple App Store 链接、Downloads/Mo 和 Est. MRR。通过分类页及公开搜索表单、精确 Apple ID 匹配，将当前保存的 200 名覆盖从 20 扩大到 196。4 个未找到的保留为缺失，未补零。网站仍未披露地区、模型和税费定义；收入保持 Est. MRR 原口径，不能当作已核实的美国区总收入。
- 可复现采集器：`python3 scripts/fetch_iosmrr.py`，先读取公开 Utilities 列表，再按应用名称搜索；分类未命中时使用公开全分类表单，最终只按 App ID 取数。月份改变会拒绝解析。没有使用登录、密钥或第三方私有接口。该脚本只更新 IOSMRR 快照，网页刷新按钮仍只更新 Apple 榜单。
- 解析器新增测试验证月下载不会读成 $/Download，收入不会拼入环比变化，月份变化会拒绝，名称相似不能替代正确 ID。21 项测试及 JS 语法检查通过。按保存的榜单，月下载有值 196 个、月收入有值 197 个；数值可来自不同地区和不同收入定义，均值不表示精度提升。
