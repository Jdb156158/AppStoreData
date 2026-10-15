# 美国区评星差评率

现有近30天文字评论差评率保持原样，右侧新增独立评星差评率。免登录可取得的是当前累计评星分布，列与详情均明确注明“当前累计”，没有把它称为近30天。

来源：Apple US App Store customer-reviews 页面，公开 GET `/us/customer-reviews/id<AppleID>?displayable-kind=11`，请求头 `X-Apple-Store-Front: 143441,12`。无需Cookie、账号、API Key或用户凭据。

解析 `.rating-count` 的总评星数和五个 `.vote` 的星级/数量；检查1–5星齐全、非负整数、星级加总等于总量。评星差评率 = 当前累计1–3星数 / 当前累计全部1–5星数，包括没有文字的评星。空分母或取数失败不显示0%。

2026-10-14实测：200个应用全部成功取得。Cleanup为64,974 / 736,293 ≈ 8.82%；Cleaner Guru为18,492 / 148,522 ≈ 12.45%。两者与文字样本差评率不同。

Apple允许开发者重置摘要评分，因此“当前累计”并不保证覆盖应用上线至今。当前接口没有时间查询或历史快照；点点匿名评分历史接口返回201000尚未登录，AppTweak匿名历史接口返回401要求API Key。尚未取得免登录近30天历史数据。

`scripts/star_ratings.py` 采集并写入 `data/star-ratings.json`，`--publish` 通过现有Keychain同步令牌写入Sites `/api/star-ratings`。GET无需登录；POST仅接受已授权同步程序。R2保存最新快照及UTC+8日期对应的每日快照，现有每日推送成功后独立更新评星，不改变飞书图片及文字内容。

实现依据：[app-store-scraper ratings.js](https://github.com/facundoolano/app-store-scraper/blob/master/lib/ratings.js)。Apple口径：[Ratings, reviews, and responses](https://developer.apple.com/app-store/ratings-and-reviews/)。
