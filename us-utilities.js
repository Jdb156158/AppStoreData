const $ = id => document.getElementById(id);
const number = value => new Intl.NumberFormat('en-US').format(value);
const compactNumber = value => new Intl.NumberFormat('en-US', {notation:'compact',maximumFractionDigits:2}).format(value);
const date = value => new Date(value).toLocaleString('zh-CN', {timeZone:'Asia/Singapore',hour12:false});
const rankScroll = $('rank-scroll'), rankScrollbar = $('rank-scrollbar');
const refreshInterval = 30 * 60 * 1000;
let loading = false, lastAttemptAt = 0;

function syncRankScrollbar() {
  const bounds = rankScroll.getBoundingClientRect();
  rankScrollbar.hidden = rankScroll.scrollWidth <= rankScroll.clientWidth;
  rankScrollbar.style.left = `${bounds.left}px`;
  rankScrollbar.style.width = `${bounds.width}px`;
  $('rank-scrollbar-width').style.width = `${rankScroll.scrollWidth}px`;
  rankScrollbar.scrollLeft = rankScroll.scrollLeft;
}

rankScroll.addEventListener('scroll',()=>{ rankScrollbar.scrollLeft = rankScroll.scrollLeft; });
rankScrollbar.addEventListener('scroll',()=>{ rankScroll.scrollLeft = rankScrollbar.scrollLeft; });
window.addEventListener('resize',syncRankScrollbar);
new ResizeObserver(syncRankScrollbar).observe(document.querySelector('.rank-table'));

function td(value, className) {
  const cell = document.createElement('td'); cell.textContent = value ?? '—';
  if (className) cell.className = className;
  return cell;
}

function monthlyMetric(average, key, currency=false) {
  const value = average?.[key], sources = average?.[key+'Sources'] || 0;
  const global = average?.[key+'ShareBasis'] === 'global';
  const cell = td(value==null?'未取得':`≈${currency?'$':''}${compactNumber(value)}`,value==null?'missing-metric':'estimate-value');
  if (value!=null) {
    const label = document.createElement('span'); label.className = 'single-source'; label.textContent = `${sources===1?'单来源':sources+' 来源'} · ${global?'全球参考':'美国推算'}`;
    cell.append(label);
    cell.title = `${global?'未取得美国数据，按用户指定使用各来源原始全球总量；IOSMRR 原始地区未披露，按全球参考处理。':'各来源先按 AppMagic 美国占比推算。'}再对可用数值取算术均值。范围阈值按数值参与，缺失不按零计；跨来源、月份及商店口径，仅作参考。`;
  }
  return cell;
}

function usSourceMetric(app, source, key) {
  const estimate = app.usEstimates?.[source]?.[key], currency = key==='revenue';
  const cell = td(estimate ? `≈${estimate.operator}${currency?'$':''}${compactNumber(estimate.value)}` : '来源未覆盖',estimate?'commercial-value':'missing-metric');
  const globalTotal = source==='AppMagic' ? app.appmagicUSEstimate?.globalTotals?.[key] : null;
  if (!estimate && globalTotal) {
    const label = document.createElement('span'); label.className = 'single-source'; label.textContent = `全球 ${globalTotal.operator}${currency?'$':''}${compactNumber(globalTotal.threshold)}`;
    cell.append(label);
    cell.title = `已取得 AppMagic ${app.appmagicUSEstimate.periodLabel}全球总量 ${globalTotal.raw}，按全球口径展示并参与参考均值；缺失不代表零。`;
  }
  if (estimate) {
    const global = estimate.shareBasis === 'global', percent = estimate.usPercent;
    const urls = {'IOSMRR':'data/iosmrr-public-snapshot.json','Sensor Tower':app.sensorTowerEstimate?.sourceUrl,'Appfigures':app.appfiguresEstimate?.sourceUrl,'AppMagic':app.appmagicUSEstimate?.sourceUrl};
    const link = document.createElement('a'); link.textContent = cell.textContent; link.href = urls[source]; link.target = '_blank'; link.rel = 'noreferrer';
    link.title = `${source} 原始数值 ${estimate.operator}${currency?'$':''}${compactNumber(estimate.rawValue)}${global?'，美国值未取得时使用全球原始总量':` × 美国 ${percent}%（AppMagic 最近30天占比）`}。范围阈值按显示数值参与均值；跨来源、月份及商店口径，仅作参考。IOSMRR 原地区未披露，按全球参考处理。`;
    const label = document.createElement('span'); label.className = 'single-source'; label.textContent = global ? (source==='IOSMRR'?'全球参考 · 地区未披露':'全球总量') : `${source==='AppMagic'?'美国':'参考美国'}占比 ${percent}%`;
    cell.replaceChildren(link,label);
  }
  return cell;
}

function qimaiMetric(estimate) {
  const value = estimate?.downloadsEstimate;
  const cell = td(value==null?'未获取':compactNumber(value),value==null?'missing-metric':'commercial-value');
  if (value!=null) {
    const link = document.createElement('a'); link.textContent = cell.textContent; link.href = estimate.sourceUrl; link.target = '_blank'; link.rel = 'noreferrer';
    link.title = `七麦 · 美国 iOS · 昨日下载预估 · 采集于 ${date(estimate.capturedAt)}（UTC+8）；绝对统计日期未核实，不参与月度均值。`;
    cell.replaceChildren(link);
    if (value===0) { const label = document.createElement('span'); label.className = 'single-source'; label.textContent = '原页显示 0'; cell.append(label); }
  }
  return cell;
}

function render(data) {
  const scrollX = window.scrollX, scrollY = window.scrollY, tableScrollLeft = rankScroll.scrollLeft;
  ReviewAnalysis.reload();
  StarRatings.reload();
  $('rank-rows').replaceChildren();
  data.apps.forEach(app => {
    const row = document.createElement('tr');
    const info = document.createElement('td'), box = document.createElement('div'); box.className = 'app-cell';
    const icon = document.createElement('img'); icon.src = app.icon; icon.alt = ''; icon.loading = 'lazy';
    const text = document.createElement('div'), link = document.createElement('a'), developer = document.createElement('p');
    link.textContent = app.name; link.href = app.url; link.target = '_blank'; link.rel = 'noreferrer';
    developer.textContent = app.developer; text.append(link,developer); box.append(icon,text); info.append(box);
    const version = td(app.version,'version-cell');
    if (app.updatedAt) { const updated = document.createElement('span'); updated.textContent = app.updatedAt.slice(0,10); version.append(updated); }
    row.append(td(String(app.rank).padStart(2,'0'),app.rank<=3?'rank-top':''),info,monthlyMetric(app.usMonthlyAverage,'downloads'),monthlyMetric(app.usMonthlyAverage,'revenueUSD',true),td(app.releasedAt?.slice(0,10)),td(app.rating==null?'—':`★ ${app.rating.toFixed(2)}`,'rating-value'),td(app.ratingCount==null?'—':number(app.ratingCount)),td(app.price==null?'—':app.price===0?'免费':`${app.currency} ${app.price.toFixed(2)}`),version,usSourceMetric(app,'IOSMRR','downloads'),usSourceMetric(app,'IOSMRR','revenue'),usSourceMetric(app,'Sensor Tower','downloads'),usSourceMetric(app,'Sensor Tower','revenue'),usSourceMetric(app,'Appfigures','downloads'),usSourceMetric(app,'Appfigures','revenue'));
    $('rank-rows').append(row);
    row.append(qimaiMetric(app.qimaiEstimate));
    row.append(usSourceMetric(app,'AppMagic','downloads'),usSourceMetric(app,'AppMagic','revenue'));
    row.append(ReviewAnalysis.cell(app),StarRatings.cell(app));
  });
  $('count').textContent = `${data.apps.length} 个应用`;
  $('feed-time').textContent = data.feedUpdatedAt ? `Apple 榜单更新：${date(data.feedUpdatedAt)}（UTC+8）` : `Apple 榜单获取：${date(data.capturedAt)}（UTC+8）`;
  $('fetch-time').textContent = `获取于 ${date(data.capturedAt)}`;
  $('source').href = data.sourceUrl;
  const estimates = data.publicMetrics;
  $('iosmrr-count').textContent = `· IOSMRR 来源覆盖 ${data.apps.filter(app=>Object.keys(app.usEstimates?.IOSMRR || {}).length).length} 个应用`;
  $('estimate-count').textContent = `参考均值 ${data.apps.filter(app=>app.usMonthlyAverage?.downloads!=null || app.usMonthlyAverage?.revenueUSD!=null).length} / ${data.apps.length}`;
  document.querySelector('.public-month').textContent = estimates ? `原始地区未披露 · ${estimates.month}` : '月份未取得';
  $('estimate-source').href = estimates?.sourceUrl || 'https://iosmrr.com/?category=utilities';
  $('estimate-note').textContent = estimates ? `数据标签：${estimates.month} · 采集于 ${date(estimates.capturedAt)}（UTC+8）。地区、方法和税费口径未披露；刷新按钮仅更新 Apple 榜单，估算仍为保存的快照。` : '公开估算快照暂未加载。';
  $('sensor-count').textContent = `· Sensor Tower 来源覆盖 ${data.apps.filter(app=>Object.keys(app.usEstimates?.['Sensor Tower'] || {}).length).length} 个应用`;
  const appfigures = data.appfiguresMetrics;
  const months = [...new Set(data.apps.map(app=>app.appfiguresEstimate?.month).filter(Boolean))];
  $('appfigures-month').textContent = `原始全球 · ${months.join(' / ') || '月份未取得'} · 商店合并`;
  $('appfigures-count').textContent = `· Appfigures 来源覆盖 ${data.apps.filter(app=>Object.keys(app.usEstimates?.Appfigures || {}).length).length} 个应用`;
  $('appfigures-note').textContent = appfigures ? `Appfigures 官方 CLI 摘要 · 采集于 ${date(appfigures.capturedAt)}（UTC+8）。全球 ${months.join(' / ')} 自然月估算，应用合并摘要未拆分平台；关联平台见数值悬停。收入扣除平台费用。缺失不表示零；表格值优先按 AppMagic 美国占比推算，缺失时使用全球原始总量，范围阈值按显示数值参与均值；刷新按钮不重新采集此快照。` : 'Appfigures 摘要暂未加载。';
  const qimai = data.qimaiMetrics;
  $('qimai-count').textContent = `· 七麦日下载覆盖 ${qimai?.coverage || 0} 个应用`;
  $('qimai-note').textContent = qimai ? `七麦 · 美国 iOS · 昨日下载预估 · 采集于 ${date(qimai.capturedAt)}（UTC+8）。${qimai.note}` : '七麦公开日下载快照暂未加载。';
  const appmagic = data.appmagicUSMetrics;
  $('appmagic-month').textContent = appmagic ? `${appmagic.periodLabel} · 美国优先 / 全球备用 · 商店合并` : '月度快照未加载';
  $('appmagic-count').textContent = `· AppMagic 月下载 ${appmagic?.downloadsCoverage || 0} / 月收入 ${appmagic?.revenueCoverage || 0} 个应用`;
  $('appmagic-note').textContent = appmagic ? `AppMagic 美国优先 / 全球备用 · ${appmagic.periodLabel} · 采集于 ${date(appmagic.capturedAt)}（UTC+8）。${appmagic.note}` : 'AppMagic 公开月度范围快照暂未加载。';
  syncRankScrollbar();
  rankScroll.scrollLeft = tableScrollLeft;
  rankScrollbar.scrollLeft = tableScrollLeft;
  window.scrollTo(scrollX,scrollY);
}

async function load(refresh=false) {
  if (loading) return;
  loading = true;
  lastAttemptAt = Date.now();
  $('refresh').disabled = true;
  $('status').classList.remove('error');
  $('status').textContent = refresh?'正在读取最新榜单数据…':'正在加载榜单数据…';
  try {
    const response = await fetch(`/api/us-utilities${refresh?'?refresh=1':''}`,{cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    render(data);
    $('status').textContent = `已检查最新数据：${date(Date.now())}（UTC+8）· 每30分钟自动刷新 · 月度估算使用已保存的第三方快照。`;
  } catch (error) {
    if (!$('rank-rows').children.length) {
      try {
        const response = await fetch('data/us-utilities.json');
        if (!response.ok) throw new Error('no snapshot');
        render(await response.json());
        $('status').textContent = '实时请求暂未成功，当前显示已保存的 Apple 数据快照。';
      } catch { $('status').textContent = '暂时无法获取 Apple 榜单，请稍后点击刷新重试。'; }
    } else $('status').textContent = '刷新失败，当前保留上次数据；请稍后重试。';
    $('status').classList.add('error');
  } finally { loading = false; $('refresh').disabled = false; }
}

$('refresh').addEventListener('click',()=>load(true));
setInterval(()=>load(true),refreshInterval);
document.addEventListener('visibilitychange',()=>{
  if (!document.hidden && Date.now()-lastAttemptAt >= refreshInterval) load(true);
});
load();
