// The rate uses the collected 30-day written-review sample, including 1–5 stars.
const reviewDialog = document.getElementById('review-dialog');
let reviewSnapshot;
let selectedReviewApp, reviewRequest = 0;

async function getReviewSnapshot() {
  if (!reviewSnapshot) reviewSnapshot = (async () => {
    let response = await fetch('/api/review-analysis', {cache:'no-store'});
    if (!response.ok) response = await fetch('data/review-analysis.json', {cache:'no-store'});
    if (!response.ok) throw new Error('评论快照暂未加载');
    return response.json();
  })().catch(error => { reviewSnapshot = null; throw error; });
  return reviewSnapshot;
}

function reviewElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = text;
  return element;
}

function writtenReviewRate(app, snapshot) {
  const total = app?.writtenReviewCount, negative = app?.negativeWrittenReviewCount;
  if (snapshot?.country !== 'us' || snapshot.source?.kind !== 'written_reviews' || app?.country !== 'us' || !['ok','partial'].includes(app.status) || !Number.isSafeInteger(total) || total <= 0 || !Number.isSafeInteger(negative) || negative < 0 || negative > total) return null;
  return {total, negative, percent:negative/total*100};
}

function reviewCell(app) {
  const cell = reviewElement('td','review-column');
  const button = reviewElement('button','review-pill');
  button.type = 'button';
  button.setAttribute('aria-label', `${app.name} 评论分析`);
  const track = reviewElement('span','review-pill-track'), fill = reviewElement('span','review-pill-fill');
  track.append(fill);
  const value = reviewElement('span','', '差评 —'), note = reviewElement('span','review-cell-note','正在加载评论…');
  button.append(track,value); cell.append(button,note);
  button.addEventListener('click',()=>openReviewAnalysis(app));
  getReviewSnapshot().then(snapshot => {
    const sample = snapshot.apps[String(app.id)], rate = writtenReviewRate(sample,snapshot);
    if (rate) {
      value.textContent = `差评 ${rate.percent.toFixed(1)}%`;
      fill.style.width = `${rate.percent}%`;
    } else button.classList.add('rate-unavailable');
    note.textContent = rate ? `${rate.negative} / ${rate.total} 条${sample.windowCovered ? '' : ' · 部分样本'} · 查看` : !sample || sample.status === 'unavailable' ? '评论暂未取得 · 点击详情' : '近30天暂无文字样本';
    button.title = '美国近30天1–3星文字评论数 ÷ 近30天取得的全部文字评论数；仅代表公开评论样本，不代表全部评星。';
  }).catch(()=>{ button.classList.add('rate-unavailable'); note.textContent = '评论加载失败 · 点击重试'; });
  return cell;
}

async function openReviewAnalysis(app) {
  selectedReviewApp = app;
  const request = ++reviewRequest;
  reviewDialog.dataset.appId = String(app.id);
  document.getElementById('review-app-name').textContent = app.name;
  document.getElementById('review-app-icon').src = app.icon;
  const content = document.getElementById('review-content');
  content.replaceChildren(reviewElement('p','review-empty','正在加载美国区近30天评论…'));
  if (!reviewDialog.open) reviewDialog.showModal();
  try {
    const snapshot = await getReviewSnapshot(), sample = snapshot.apps[String(app.id)];
    if (request !== reviewRequest || reviewDialog.dataset.appId !== String(app.id) || !reviewDialog.open) return;
    content.replaceChildren();
    const rate = writtenReviewRate(sample,snapshot), summary = reviewElement('section','review-summary');
    const title = reviewElement('div','review-summary-title');
    title.append(reviewElement('strong','', '文字评论差评率'),reviewElement('span','review-rate',rate ? `${rate.percent.toFixed(1)}%` : '—'));
    const track = reviewElement('div','review-summary-track'), fill = reviewElement('div','');
    if (rate) { fill.style.width = `${rate.percent}%`; track.append(fill); }
    else track.classList.add('rate-unavailable');
    summary.append(title,track,
      reviewElement('p','review-formula','差评率 = 近30天 1–3 星文字评论数 ÷ 近30天取得的全部文字评论数'),
      reviewElement('p','review-rating-counts',rate ? `1–3星文字评论 ${rate.negative.toLocaleString()} 条 / 全部文字评论 ${rate.total.toLocaleString()} 条；不包含无文字评星。` : '当前没有可用的近30天文字评论样本，暂不计算差评率。'));
    content.append(summary);
    const period = value => new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Singapore',hour12:false});
    content.append(reviewElement('p','review-period',`美国 · 采样范围 ${period(snapshot.window.startAt)} — ${period(snapshot.window.endAt)}（UTC+8）`));
    if (!sample || sample.status === 'unavailable') {
      content.append(reviewElement('p','review-empty','该应用的美国区评论接口暂未成功返回；不表示没有差评。'));
      return;
    }
    const sampleNote = reviewElement('div','review-sample-note');
    sampleNote.append(reviewElement('strong','',`已取得 ${sample.writtenReviewCount.toLocaleString()} 条文字评论，其中 ${sample.negativeWrittenReviewCount.toLocaleString()} 条为 1–3 星。`),
      reviewElement('p','',sample.windowCovered ? '已翻页至30天之前或公开列表末尾；这是接口可取得的文字样本，不能代表全部评星。' : '公开接口仅返回最近最多500条评论，或部分分页请求失败；当前为不完整的30天文字样本。'));
    content.append(sampleNote);
    const themeSection = reviewElement('section','review-themes');
    themeSection.append(reviewElement('h3','', '排名前 10 差评主题'),reviewElement('p','review-section-note','按文字差评关键词匹配的评论条数排序；同一条可属于多个主题，分类仅作参考。'));
    const themes = reviewElement('ol','review-theme-list'), max = sample.themes[0]?.count || 1;
    sample.themes.forEach((theme,index) => {
      const item = reviewElement('li','review-theme');
      const label = reviewElement('div','review-theme-label');
      label.append(reviewElement('strong','',theme.label),reviewElement('span','',theme.keywords));
      const bar = reviewElement('div','review-theme-track'), fill = reviewElement('div','');
      fill.style.width = `${theme.count/max*100}%`; bar.append(fill);
      item.append(reviewElement('span','review-theme-rank',String(index+1)),label,bar,reviewElement('strong','review-theme-count',`${theme.count}条`));
      themes.append(item);
    });
    themeSection.append(themes);
    if (!sample.themes.length) themeSection.append(reviewElement('p','review-empty',sample.negativeWrittenReviewCount ? '当前差评未匹配到预设主题关键词，原文见下方。' : '当前文字样本中未取得近30天1–3星评论。'));
    content.append(themeSection);
    const examples = reviewElement('section','review-examples');
    const detailNote = sample.reviews.length < sample.negativeWrittenReviewCount ? `已取得 ${sample.reviews.length} / ${sample.negativeWrittenReviewCount} 条差评详情，其余暂未补齐。` : '展示已采集样本中的全部1–3星文字差评。';
    examples.append(reviewElement('h3','',`近30天文字差评 · ${sample.reviews.length} 条`),reviewElement('p','review-section-note',`${detailNote}按 Apple 评论更新日期倒序。英文原文下附中文机器翻译，仅供参考。`));
    sample.reviews.forEach(review => {
      const card = reviewElement('article','review-example');
      const heading = reviewElement('div','review-example-heading');
      heading.append(reviewElement('span','review-star-badge',`${review.stars} 星`),reviewElement('h4','',review.title || '无标题'));
      card.append(heading,reviewElement('p','review-example-meta',`${review.author || '匿名'} · ${period(review.updatedAt)}（UTC+8）${review.version ? ' · 版本 '+review.version : ''}`),reviewElement('p','review-original',review.body));
      const translation = reviewElement('section','review-translation');
      const chinese = review.translation;
      translation.append(reviewElement('p','review-translation-label','中文翻译 · 机器翻译'));
      const attribution = reviewElement('a','review-translation-provider','OPUS-MT');
      attribution.href = 'https://huggingface.co/Helsinki-NLP/opus-mt-en-zh'; attribution.target = '_blank'; attribution.rel = 'noreferrer';
      translation.firstChild.append(' · ',attribution);
      if (chinese?.language === 'zh-CN' && chinese.body) {
        translation.append(reviewElement('p','review-translation-body',chinese.body));
        translation.title = `${chinese.provider} 英译中，仅供参考，请以原文为准。`;
      } else translation.append(reviewElement('p','review-translation-body','中文翻译暂未取得，请先查看上方原文。'));
      card.append(translation);
      examples.append(card);
    });
    if (!sample.reviews.length) examples.append(reviewElement('p','review-empty',rate ? '当前文字评论样本中没有1–3星评论，样本差评率为0%。' : '当前没有可用的近30天文字评论样本。'));
    content.append(examples);
    const source = reviewElement('p','review-source');
    const link = reviewElement('a','', 'Apple 美国区评论来源 ↗'); link.href = sample.sourceUrl; link.target = '_blank'; link.rel = 'noreferrer';
    source.append(link,reviewElement('span','',` · 采集于 ${period(sample.capturedAt)}（UTC+8）。日期使用 Apple updated 字段，评论可能经用户修改。`));
    content.append(source);
  } catch {
    if (request !== reviewRequest || !reviewDialog.open) return;
    content.replaceChildren(reviewElement('p','review-empty','评论暂时加载失败，请关闭后点击重试。'));
  }
}

document.getElementById('review-close').addEventListener('click',()=>reviewDialog.close());
reviewDialog.addEventListener('click',event=>{ if (event.target === reviewDialog) reviewDialog.close(); });
window.ReviewAnalysis = {cell:reviewCell, reload:()=>{
  reviewSnapshot = null;
  if (reviewDialog.open && selectedReviewApp) openReviewAnalysis(selectedReviewApp);
}};
