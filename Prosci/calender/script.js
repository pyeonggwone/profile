let currentLang = 'en';
const cache = {};
const assetVersion = '20260426-remove-adkar-progress';

async function loadLang(lang) {
    if (cache[lang]) return cache[lang];
    const file = lang === 'en' ? 'en.json' : 'kr.json';
    const res = await fetch(`${file}?v=${assetVersion}`);
    const data = await res.json();
    cache[lang] = data;
    return data;
}

function badgeClass(state) {
    if (state === 'done') return 'done';
    if (state === 'active') return 'active';
    return 'upcoming';
}

function externalLink(url, label) {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
}

function renderTask(task) {
    if (typeof task === 'string') return `<li>${task}</li>`;
    return `<li>${task.url ? externalLink(task.url, task.text) : task.text}</li>`;
}

function renderMilestone(m) {
    const stateClass = m.state ? ` ${m.state}` : '';
    const bc = badgeClass(m.state);

    let body = '';
    if (m.classGrid) {
        const days = m.classGrid.map(d =>
            `<div class="class-day">
        <div class="label">${d.url ? externalLink(d.url, d.label) : d.label}</div>
        <div class="time">${d.time}</div>
      </div>`
        ).join('');
        body = `<div class="class-grid">${days}</div>`;
    } else {
        const items = m.tasks.map(renderTask).join('');
        body = `<ul class="tasks">${items}</ul>`;
    }

    return `
    <div class="milestone${stateClass}">
      <div class="date-col">
        <div class="month">${m.date.month}</div>
        <div class="day">${m.date.day}</div>
      </div>
      <div class="info">
        <div class="top">
          <span class="week-tag">${m.week}</span>
          <span class="badge ${bc}">${m.badge}</span>
        </div>
        <h3>${m.title}</h3>
        ${body}
      </div>
    </div>`;
}

async function render(lang) {
    const data = await loadLang(lang);

    document.title = data.pageTitle;
    document.documentElement.lang = lang;
    document.getElementById('header-title').textContent = data.header.title;
    document.getElementById('header-subtitle').textContent = data.header.subtitle;
    document.getElementById('lang-btn').textContent = data.langBtn;
    document.getElementById('footer-text').textContent = data.footer;
    document.getElementById('header-links').innerHTML = (data.header.links || [])
        .map(link => externalLink(link.url, link.label))
        .join('');
    document.getElementById('timeline').innerHTML =
        data.milestones.map(renderMilestone).join('');
}

async function toggleLang() {
    currentLang = currentLang === 'en' ? 'kr' : 'en';
    await render(currentLang);
}

document.getElementById('lang-btn').addEventListener('click', toggleLang);
render(currentLang);