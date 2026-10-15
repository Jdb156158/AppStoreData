const starDialog = document.getElementById('star-dialog');
let starSnapshot;
let selectedStarApp, starRequest = 0;

async function getStarSnapshot() {
  if (!starSnapshot) starSnapshot = (async () => {
    let response = await fetch('/api/star-ratings', {cache:'no-store'});
    if (!response.ok) response = await fetch('data/star-ratings.json', {cache:'no-store'});
    if (!response.ok) throw new Error('评星数据未加载');
    return response.json();
  })().catch(error=>{ starSnapshot = null; throw error; });
  return starSnapshot;
}

function cumulativeStarRate(sample) {
  if (sample?.status !== 'ok' || sample.country !== 'us' || sample.scope !== 'current_cumulative' || !Array.isArray(sample.byStar) || sample.byStar.length !== 5 || !sample.byStar.every(n=>Number.isSafeInteger(n) && n>=0) || sample.byStar.reduce((sum,n)=>sum+n,0) !== sample.total || sample.total <= 0) return null;
  const negative = sample.byStar.slice(0,3).reduce((sum,n)=>sum+n,0);
  return {total:sample.total, negative, percent:negative/sample.total*100};
}

function starCell(app) {
  const cell = reviewElement('td','review-column star-column');
  const button = reviewElement('button','review-pill'); button.type = 'button';
  button.setAttribute('aria-label',`${app.name} 评星差评率`);
  const track = reviewElement('span','review-pill-track'), fill = reviewElement('span','review-pill-fill'); track.append(fill);
  const value = reviewElement('span','', '差评 —'), note = reviewElement('span','review-cell-note','正在加载评星…');
  button.append(track,value); cell.append(button,note);
  button.addEventListener('click',()=>openStarDetails(app));
  getStarSnapshot().then(snapshot=>{
    const sample = snapshot.apps[String(app.id)], rate = cumulativeStarRate(sample);
    if (rate) { value.textContent = `差评 ${rate.percent.toFixed(1)}%`; fill.style.width = `${rate.percent}%`; }
    else button.classList.add('rate-unavailable');
    note.textContent = rate ? `累计 · ${rate.negative.toLocaleString()} / ${rate.total.toLocaleString()}` : '评星暂未取得 · 查看';
    button.title = 'Apple 美国区当前累计1–3星评星数 ÷ 全部累计评星数，包括未写文字的评星；不是最近30天。';
  }).catch(()=>{button.classList.add('rate-unavailable');note.textContent = '加载失败 · 点击重试';});
  return cell;
}

async function openStarDetails(app) {
  selectedStarApp = app;
  const request = ++starRequest;
  starDialog.dataset.appId = String(app.id);
  document.getElementById('star-app-name').textContent = app.name;
  document.getElementById('star-app-icon').src = app.icon;
  const content = document.getElementById('star-content');
  content.replaceChildren(reviewElement('p','review-empty','正在加载美国区评星数据…'));
  if (!starDialog.open) starDialog.showModal();
  try {
    const snapshot = await getStarSnapshot(), sample = snapshot.apps[String(app.id)], rate = cumulativeStarRate(sample);
    if (request !== starRequest || !starDialog.open || starDialog.dataset.appId !== String(app.id)) return;
    content.replaceChildren();
    const summary = reviewElement('section','review-summary'), title = reviewElement('div','review-summary-title');
    title.append(reviewElement('strong','', '当前累计评星差评率'),reviewElement('span','review-rate',rate ? `${rate.percent.toFixed(1)}%` : '—'));
    const track = reviewElement('div','review-summary-track'), fill = reviewElement('div','');
    if (rate) {fill.style.width = `${rate.percent}%`;track.append(fill);} else track.classList.add('rate-unavailable');
    summary.append(title,track,reviewElement('p','review-formula','评星差评率 = 当前累计1–3星评星数 ÷ 当前累计全部1–5星评星数'),
      reviewElement('p','review-rating-counts',rate ? `1–3星 ${rate.negative.toLocaleString()} 次 / 全部评星 ${rate.total.toLocaleString()} 次，包含未写文字的评星。` : '未取得可用评星数据，无法计算百分比。'));
    content.append(summary,reviewElement('p','review-period','美国 · 当前累计口径，与左侧近30天文字评论差评率的统计范围不同。'));
    if (!sample || sample.status !== 'ok') {content.append(reviewElement('p','review-empty','该应用的美国区评星数据暂未取得；缺失不代表0%。'));return;}
    const breakdown = reviewElement('section','review-themes');
    breakdown.append(reviewElement('h3','', '1–5星评星分布'));
    const list = reviewElement('ol','review-theme-list');
    for (let star=5;star>=1;star--) {
      const count = sample.byStar[star-1], item = reviewElement('li','star-breakdown-row');
      const track = reviewElement('div','review-theme-track'), fill = reviewElement('div','');
      fill.style.width = `${sample.total ? count/sample.total*100 : 0}%`;
      fill.className = star<=3 ? 'star-negative' : 'star-positive';track.append(fill);
      item.append(reviewElement('strong','',`${star} 星`),track,reviewElement('span','',count.toLocaleString()),reviewElement('span','',sample.total ? `${(count/sample.total*100).toFixed(1)}%` : '—'));
      list.append(item);
    }
    breakdown.append(list);content.append(breakdown);
    content.append(reviewElement('p','review-empty','最近30天评星差评率：尚缺历史星级基线，未用累计数或文字评论数代替。已开始保存每日星级快照。'));
    const source = reviewElement('p','review-source'), link = reviewElement('a','', 'Apple 美国区评星来源 ↗');
    link.href = sample.sourceUrl;link.target = '_blank';link.rel = 'noreferrer';
    source.append(link,reviewElement('span','',` · 采集于 ${new Date(sample.capturedAt).toLocaleString('zh-CN',{timeZone:'Asia/Singapore',hour12:false})}（UTC+8）。无需账号。Apple允许重置摘要评分，当前累计不保证覆盖上线至今。`));
    content.append(source);
  } catch {
    if (request === starRequest && starDialog.open) content.replaceChildren(reviewElement('p','review-empty','评星数据暂时加载失败，请关闭后点击重试。'));
  }
}

document.getElementById('star-close').addEventListener('click',()=>starDialog.close());
starDialog.addEventListener('click',event=>{if(event.target===starDialog)starDialog.close();});
window.StarRatings = {cell:starCell,reload:()=>{
  starSnapshot=null;
  if (starDialog.open && selectedStarApp) openStarDetails(selectedStarApp);
}};
