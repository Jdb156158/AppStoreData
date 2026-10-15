# 评论中文翻译

差评详情保留英文标题、正文、作者、星级和时间，在英文正文下展示中文正文，并标注机器翻译。
翻译不改变文字差评率的分子、分母或评论主题统计。缺少译文时显示提示，不将原文冒充中文译文。

采用 Helsinki-NLP 的 [OPUS-MT en→zh](https://huggingface.co/Helsinki-NLP/opus-mt-en-zh)，
使用 [gaudi 的 CTranslate2 转换](https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/tree/8ed73397ed3c030e27077bc5bd0a8e418097ca2e)。
原模型作者 Jörg Tiedemann、Santhosh Thottingal，许可证 CC BY 4.0。
模型仅在本机运行，网站访客不需要下载模型。页面保留模型来源链接。
译文仅供参考；模型可能误译语气、品牌、缩写及复杂句子，应以英文原文为准。

## 本机依赖

隔离环境 `.local/translation-venv` 中安装 `ctranslate2`、`sentencepiece`、`langid`。
已验证 Python 3.12、CTranslate2 4.8.3、SentencePiece 0.2.2、langid 1.1.6。
目录 `.local/translation-model/opus-mt-en-zh` 保存上述固定模型版本的
`config.json`、`shared_vocabulary.json`、`source.spm`、`target.spm`、`model.bin`。
依赖、模型和缓存均被 Git 忽略，不发布到网站。

`scripts/review_analysis.py` 采集完成后，通过隔离 Python 调用 `scripts/translate_reviews.py`。
语言识别为英文的评论生成译文，其他语言当前不生成中文翻译。
翻译评论正文；长文本拆分，避免输入长度限制丢失后半段。
Marian 输入包含简体中文目标标记和结束标记。
针对 free trial、storage 的误译应用试用、存储空间术语修正。

本地缓存 `.local/review-translations.json` 以模型版本和原文的 SHA-256 为键；
原文变化重新翻译，未变化复用译文。译文随评论快照一起通过现有授权 API 同步，
不额外发送飞书消息、不提供任意文本翻译接口。

单独补齐本地快照：

```sh
.local/translation-venv/bin/python scripts/translate_reviews.py
```

采集最新近30天评论、补齐翻译并更新线上快照：

```sh
python3 scripts/review_analysis.py --publish
```
