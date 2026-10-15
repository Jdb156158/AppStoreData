const $ = (id) => document.getElementById(id);
const number = (value) => new Intl.NumberFormat('zh-CN').format(value);
let snapshot;

function cell(text) {
  const td = document.createElement('td');
  td.textContent = text;
  return td;
}

function showRatings(key) {
  const rating = snapshot.diandian.ratings[key];
  $('rating-average').textContent = rating.average.toFixed(2);
  $('rating-count').textContent = `${number(rating.count)} 个评分`;
  $('rating-label').textContent = rating.label;
  $('rating-bars').replaceChildren();
  rating.stars.forEach((count, i) => {
    const row = document.createElement('div');
    row.className = 'rating-bar';
    row.innerHTML = `<span>${5 - i} 星</span><div class="track"><div class="fill" style="width:${count / rating.count * 100}%"></div></div><span class="count">${number(count)}</span>`;
    row.title = `${5 - i} 星：${(count / rating.count * 100).toFixed(2)}%`;
    $('rating-bars').append(row);
  });
  document.querySelectorAll('[data-rating]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.rating === key)));
}

async function load() {
  try {
    const response = await fetch('data/snapshot.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    snapshot = await response.json();
    const d = snapshot.diandian, a = snapshot.apple;
    $('name').textContent = a.trackName;
    $('icon').src = a.artworkUrl512 || a.artworkUrl100;
    $('subtitle').textContent = d.subtitle;
    $('version').textContent = `v${a.version}`;
    $('original').href = d.source;
    $('captured').textContent = `获取于 ${new Date(d.capturedAt).toLocaleString('zh-CN', {timeZone:'Asia/Singapore', hour12:false})}（UTC+8）`;
    const metrics = [
      ['分类榜排名', `#${d.rank.value}`, `${d.rank.category} · 点点页面`],
      ['当前版本评分', d.ratings.current.average.toFixed(2), `共 ${number(d.ratings.current.count)} 个评分`],
      ['App 指数', number(d.appIndex), '点点页面展示指数'],
      ['最新更新', a.currentVersionReleaseDate.slice(0,10), `版本 ${a.version} · Apple`]
    ];
    metrics.forEach(([label,value,note]) => {
      const el = document.createElement('div'); el.className = 'metric';
      el.innerHTML = `<div class="label">${label}</div><strong>${value}</strong><small>${note}</small>`;
      $('metrics').append(el);
    });
    $('scope').textContent = `${d.overview.scope} / ${d.overview.period}`;
    [['download','下载量'], ['income','收入']].forEach(([key,label]) => {
      const item = d.overview[key], el = document.createElement('article'); el.className = 'estimate';
      const top = document.createElement('div'); top.className = 'estimate-top';
      const title = document.createElement('span'); title.textContent = label;
      const value = document.createElement('strong'); value.textContent = item.display;
      top.append(title,value); el.append(top);
      const change = document.createElement('div'); change.className = `change ${item.changePercent < 0 ? 'down' : 'up'}`;
      change.textContent = `${item.changePercent < 0 ? '↓' : '↑'} ${Math.abs(item.changePercent).toFixed(2)}% · 原页展示变化`;
      el.append(change);
      const share = document.createElement('div'); share.className = 'share';
      const china = document.createElement('i'); china.style.width = `${item.chinaShare}%`; share.append(china); el.append(share);
      const labels = document.createElement('small'); labels.innerHTML = `<span>中国 ${item.chinaShare}%</span><span>其他地区 ${100-item.chinaShare}%</span>`; el.append(labels);
      $('estimates').append(el);
    });
    $('estimate-note').textContent = d.overview.note;
    d.versions.forEach((item,i) => {
      const tr = document.createElement('tr'), versionCell = cell(item.version);
      if (i === 0) { const tag = document.createElement('small'); tag.textContent = '当前'; versionCell.append(tag); }
      tr.append(versionCell,cell(item.date),cell(`${item.changes} 处`)); $('version-rows').append(tr);
    });
    d.purchases.forEach(item => { const tr = document.createElement('tr'); tr.append(cell(item.name),cell(item.price)); $('purchase-rows').append(tr); });
    const fields = [
      ['App ID', a.trackId], ['Bundle ID', a.bundleId], ['开发者', a.artistName], ['供应商', a.sellerName],
      ['发布日期', a.releaseDate.slice(0,10)], ['当前版本', a.version], ['安装包大小', `${(Number(a.fileSizeBytes)/1024/1024).toFixed(2)} MB`], ['系统要求', `iOS ${a.minimumOsVersion}+`],
      ['分类', a.genres.join(' / ')], ['年龄分级', a.contentAdvisoryRating], ['支持语言', a.languageCodesISO2A.join(' / ')], ['地区', '中国'], ['备案号（点点）', d.registration], ['游戏版号（点点）', d.gameLicense]
    ];
    fields.forEach(([label,value]) => { const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = label; dd.textContent = value; $('info-list').append(dt,dd); });
    $('description').textContent = a.description;
    $('release-notes').textContent = a.releaseNotes || '未获取更新说明';
    (a.screenshotUrls || []).forEach((src,i) => { const img = document.createElement('img'); img.src = src; img.alt = `${a.trackName}应用截图 ${i+1}`; img.loading = 'lazy'; $('screenshots').append(img); });
    $('apple-link').href = snapshot.appleSource;
    $('unavailable').textContent = d.unavailable.join(' · ');
    showRatings('current');
    $('dashboard').hidden = false; $('status').hidden = true; $('export').disabled = false;
  } catch (error) { $('status').textContent = `数据读取失败：${error.message}。请通过本地 HTTP 服务打开网页。`; }
}

document.querySelectorAll('[data-rating]').forEach(button => button.addEventListener('click', () => showRatings(button.dataset.rating)));
$('export').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(snapshot,null,2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'appstoredata-989673964.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
});
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => { if (entry.isIntersecting) document.querySelectorAll('nav a').forEach(a => a.classList.toggle('active',a.hash === `#${entry.target.id}`)); });
}, {rootMargin:'-10% 0px -65% 0px'});
document.querySelectorAll('section[id]').forEach(section => observer.observe(section));
load();
