# 美区工具畅销榜 Top 20

本次已实际验证 Apple 公共 RSS 返回 HTTP 200、20 个应用，标题为 `iTunes Store: Top Grossing`，全部应用的分类 ID 为 `6002`（Utilities）。没有使用点点或 Apple 用户的登录 Cookie、token、API Key。

排名接口：

```text
https://itunes.apple.com/us/rss/topgrossingapplications/limit=20/genre=6002/json
```

评分、评分数和最新版本通过 `https://itunes.apple.com/lookup?id=<逗号分隔的20个App ID>&country=us` 补充，排名始终保留 RSS 返回顺序，未按评分或下载价格重新排序。

新增“初始上架时间”使用 Lookup 的 `releaseDate`；Lookup 不可用时使用 RSS 的 `im:releaseDate`，不使用 `currentVersionReleaseDate` 冒充初始上架日期。

表格新增下载量（历史累计、上个月）与总收入（历史累计、上个月），延续美国区口径，收入使用 USD。上个月按 UTC+8 的上一个完整自然月计算，本次为 `2026-09`；跨年时正确切换为上一年 12 月。

用户接受第三方估算。早期检查的 [AppMagic 应用页](https://appmagic.rocks/iphone/cleanup-phone-storage-cleaner/1510944943) 在匿名浏览状态下将下载、收入小部件标为“登录以解锁”；[Sensor Tower 应用页](https://app.sensortower.com/overview/1510944943?country=US) 的直接请求返回安全验证，浏览器未取得可核对的月度响应。其公开索引摘要现已放在独立全球对照表，未将月度数值累加或外推为历史累计。

因此四个下载／收入字段目前为 `null`，页面明确显示“待获取”，不表示 0。已预留用户要求的显示列，但**这四项实际数据尚未取得**。后续仍需可用的第三方估算数据源或对应导出数据，才能填入有来源与口径依据的数值；本次未使用用户登录会话。

## 2026-10-12 公开估算补充

下载量、总收入两组指标位于应用名称右侧（历史累计、月度均值）。IOSMRR 与 Sensor Tower 原始估算分别排在表格最后，来源说明位于同一卡片的展开区。估算覆盖当前榜单 20/20 个 App ID。来源为 [IOSMRR 工具榜](https://iosmrr.com/?category=utilities) 的匿名可见表格，页面标签为 `DATA · SEP 2026`。下载字段原名 `Downloads/Mo`，收入字段原名 `Est. MRR`。只去掉美元符号和逗号转换成整数；未按排名或名称匹配，未外推历史累计。

**IOSMRR 没有在所读页面披露统计地区、计算方法和税费口径**。页面国旗位于开发者名称旁，不能解释为销售地区。这里只展示提供方公开发布的估算，不认定其为美国区数据，也不认定 Est. MRR 等同于当月总收入或精确的订阅经常性收入。Cleaner Guru 等应用的下载估算异常偏低，未擅自修改，使用前应与授权数据核对。

表格最后的 Sensor Tower 两列展示 9 个应用的全球 iOS 下载与收入公开摘要。地区明确为 `Worldwide`，时间原名 `Last Month`，但具体年月未核实。各摘要抓取时间不同（包括三个月前的 Robokiller 摘要），不能与 IOSMRR 的 2026-09 数据视作同月比较。小于范围保留为 `<5K`，未转成 5,000 或零。每行保留实际检索返回的来源 URL 与索引抓取时间。

这两份补充是**保存的公开网页／索引快照，不是可自动刷新的第三方 API**。Apple 刷新会按 App ID 合并已有快照，并保留估算原始采集时间；新上榜但快照未覆盖的应用显示“来源未覆盖”。页面刷新不会声称估算已重新获取。

复现采集：匿名打开 IOSMRR 首页，点击 Utilities，读取可见表格中 Apple 链接的 App ID，筛选当前 Apple 榜单的 20 个 ID，保存表头月份和原始下载／收入文本到 `data/iosmrr-public-snapshot.json`。Sensor Tower 对照源由应用名称加 `Last month` 搜索取得，仅选 URL App ID 或 iOS publisher 下明确对应应用的行；记录到 `data/sensortower-public-snapshot.json`。

`/api/us-utilities` 和本地保存的 `data/us-utilities.json` 已包含 `publicMetrics`、每个应用的 `publicEstimate` 与 `sensorTowerMetrics`。美国区四项字段仍独立保持空值。接口自动获取完整美国区和历史累计估算这部分尚未解决。

Apple 的 [Sales and Finance 文档](https://developer.apple.com/documentation/appstoreconnectapi/sales-and-finance) 说明这类报告属于开发者自己的应用，且需要 Team Key；它不能作为这 20 个竞品的匿名销量／收入接口。

`scripts/us_utilities.py` 验证榜单路径、Top Grossing 标题、20 条数据、Utilities 分类及应用 ID 去重。任一条件不符就报错，避免把免费榜或付费榜当成畅销榜。

`server.py` 提供本地 `/api/us-utilities`，仅向上述固定 Apple 数据源发送匿名请求。普通请求缓存 5 分钟；`?refresh=1` 重新拉取。未启用定时后台任务，网页打开或手动刷新时才请求。页面分别显示 RSS 更新时间与获取时间，统一以 UTC+8 展示。

下载价格来自 RSS；畅销榜可包含免费下载、通过应用内购买产生收入的应用。Apple 接口没有返回实际收入金额或下载数量；网页的月度估算由上述第三方公开快照单独提供。

评分等 Lookup 元数据短暂失败时仍可展示 RSS 的真实排名、名称、图标、开发者；缺失元数据显示“—”。排名请求失败时，网页保留已有数据或加载本地快照，明确显示未能实时刷新。

文件：

- `data/apple-us-utilities-raw.json`：实际 RSS 原始响应。
- `data/us-utilities.json`：整理后的 20 个应用及来源、时间。
- `us-utilities.html`、`us-utilities.js`、`us-utilities.css`：独立榜单展示页。
- `tests/test_us_utilities.py`：真实响应顺序校验及错误榜单、分类、数量、重复 ID 的拒绝测试。

## 点点 API 研究补充

本次通过公开前端脚本还原了请求签名，匿名调用 `/pc/app/v1/rank` 的结果从 `100009 sign error` 变为 `201000 尚未登录`。这证明签名能通过验证，但该端点仍需要服务端认证。用户要求不依赖登录会话后，停止这一路径，榜单页全部采用 Apple 匿名接口。

上一份点点研究记录描述第一次调查的状态；这次是后续进展，不能将“签名验证通过”解释为“匿名读取点点数据成功”。

## 月度均值

用户要求前面的月下载及月收入取各第三方平均值。`monthlyAverage` 按 App ID 使用 IOSMRR 和 Sensor Tower 中可解析的精确点估算求算术均值，字段分别为 `downloads`、`revenueUSD`，同时记录各自的来源数。缺失或 `<5K` 等范围不计入分母；单来源显示原值并注明“单来源”，全缺失保持空值；0 是有效点估算。K/M 换算为 1,000/1,000,000。两来源月份、地区、收入定义未对齐，均值仅供参考，不表示美国区上一自然月的已核实数据，也不是置信区间或独立模型综合结果。各提供方可能使用相关上游数据，不能把两者数量视为精度保证。历史累计仍为空，未用月收入或月下载外推。

本次 GitHub 方法调查见 [github-data-research.md](github-data-research.md)。

## 2026-10-13 Appfigures 摘要

已通过用户授权的官方 CLI 4.0.0 获取本次榜单 20/20 个应用的全球 2026-09 摘要，保存到 `data/appfigures-public-snapshot.json`。使用官方 CLI 的 `api /unified-apps/search`，展开 `unified-app,product,estimates`；搜索名称只用于发现候选，最终按 iOS 产品的 `vendor_identifier` 与 Apple App ID 精确匹配。保留原始响应、自然月起止日期、阈值标记、关联平台和无令牌的应用来源链接。没有升级套餐或购买积分。

表格最后新增 Appfigures 月下载、月收入两列，继续使用 K/M/B 与美元符号。摘要为全球应用合并值，部分应用关联 iOS 和 Android 等多个平台，未请求平台拆分；数值下方注明合并摘要，悬停显示关联平台。收入为扣除平台费用后的估算，未换算为税前或扣费前收入。Sideline 缺少下载值，保持缺失；Cleaner Guru 的下载为上界 `≤5K`，未当成精确 5,000。

`monthlyAverage` 现使用 IOSMRR、Sensor Tower、Appfigures 的有效点估算计算用户要求的算术均值，任何来源的范围值都不计入分母，0 仍是有效值。月份、地区、平台、收入定义未对齐，均值不能解释为美国区 iOS 的实际月收入或下载量。没有取得历史累计，也没有外推。

重新采集可运行 `python3 scripts/fetch_appfigures.py`，需要 PATH 中有 pnpm 和 Node 22+，以及已登录的 CLI；随后重新获取 Apple 榜单以合并快照。页面刷新仅更新 Apple，第三方摘要继续显示实际采集时间。凭据由官方 CLI 存在本机凭据管理器中，不写入网页或数据文件。

横向滚动条固定在浏览器视口底部，与表格位置和横向滚动范围同步；查看列表上方或中段时即可操作。表格原生底部滚动条隐藏，触控板／触摸横向滚动仍保留。已验证固定条操作可同步表格、表格横向滚动可反向同步固定条，列表中段时固定条仍贴合窗口底部。


## 2026-10-13 扩展到前 200 名

实测 RSS 的 `limit=200` 仍仅返回 100 条。现改用 Apple `https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewTop?genreId=6002&popId=38`，请求头 `X-Apple-Store-Front: 143441,29` 表示美国 iPhone 商店。方法参考 [parse-tunes 的榜单实现](https://github.com/tweaselORG/parse-tunes/blob/main/src/endpoints/top-charts.ts)，未安装或运行该库。

读取所选榜单的 `adamIds`，核对畅销榜 ID 38、Utilities 6002、美国 iPhone storefront 和 200 个唯一 ID，保留 Apple 顺序。Lookup 使用全部 200 个 ID、`country=us&limit=200`；当前返回全部 200 个应用的元数据。原始榜单保存于 `data/apple-us-utilities-chart-raw.json`，Lookup 保存于 `data/apple-us-utilities-lookup.json`。榜单接口没有已核实的排名更新时间，页面显示实际获取时间；响应 properties.timestamp 未用作榜单更新时间。

原有第三方快照继续按 App ID 合并；Appfigures 摘要补采范围扩大到当前 200 个应用。缺失或不匹配的来源不按名称猜配，不填成零，不参与均值。页面保持单个表格和窗口底部同步横向滚动条。

本轮 Appfigures 补采匹配 174/200 个应用；剩余 26 个未取得可核对摘要，记录在快照 unavailable 中。部分下载量只提供范围，范围值不参与月度均值。
