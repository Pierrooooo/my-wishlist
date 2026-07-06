const WRAP_COLORS = ['var(--coral)', 'var(--teal)', 'var(--yellow)'];

let items = [];
let currentFilter = 'Tous';

function hostnameOf(url){
  try{ return new URL(url).hostname.replace('www.', ''); } catch(e){ return url; }
}

function escapeHTML(str){
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

async function fetchPreview(url){
  try{
    const r = await fetch('https://api.microlink.io/?url=' + encodeURIComponent(url));
    const j = await r.json();
    if(j.status === 'success' && j.data){
      const infos = [];
      if(j.data.description){
        const desc = j.data.description.trim();
        if(desc) infos.push(desc.length > 90 ? desc.slice(0, 90) + '…' : desc);
      }
      return {
        title: j.data.title || hostnameOf(url),
        image: (j.data.image && j.data.image.url) ? j.data.image.url : null,
        publisher: j.data.publisher || hostnameOf(url),
        infos
      };
    }
  }catch(e){}
  return { title: hostnameOf(url), image: null, publisher: hostnameOf(url), infos: [] };
}

function cardHTML(it, idx){
  const tilt = (idx % 2 === 0 ? -1 : 1) * (4 + (idx % 3) * 2);
  const wrap = WRAP_COLORS[idx % WRAP_COLORS.length];
  const frontVisual = it.image
    ? `<div class="front-img" style="background-image:url('${it.image.replace(/'/g, "%27")}')"></div>`
    : `<div class="front-placeholder" style="--wrap-color:${wrap}">🎁</div>`;
  const infosBlock = (it.infos && it.infos.length)
    ? `<div class="infos-row">${it.infos.map(i => `<span class="info-chip">${escapeHTML(i)}</span>`).join('')}</div>`
    : '';
  const categoryBadge = it.category
    ? `<div class="category-badge">${escapeHTML(it.category)}</div>`
    : '';
  return `
    <div class="gift-card" style="transform:rotate(${tilt}deg)">
      <div class="gift-card-flip" onclick="this.parentElement.classList.toggle('is-open')">
        <div class="gift-card-inner">
          <div class="gift-front">
            ${categoryBadge}
            ${frontVisual}
            <div class="front-overlay">
              <div class="front-title">${escapeHTML(it.title || 'Idée cadeau')}</div>
            </div>
          </div>
          <div class="gift-back">
            <div class="back-icon">🎁</div>
            <div class="publisher">${escapeHTML(it.publisher || '')}</div>
            ${infosBlock}
            <a class="cta" href="${it.url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Voir le produit ↗</a>
          </div>
        </div>
      </div>
    </div>`;
}

function renderFilters(){
  const bar = document.getElementById('filterBar');
  const categories = ['Tous', ...new Set(items.filter(i => i.see).map(i => i.category).filter(Boolean))];
  if(categories.length <= 2){ bar.innerHTML = ''; return; } // pas besoin de filtres pour 1 seule catégorie
  bar.innerHTML = `<div class="filter-bar">${categories.map(cat => `
    <button class="filter-btn ${cat === currentFilter ? 'active' : ''}" onclick="setFilter('${cat.replace(/'/g, "\\'")}')">${escapeHTML(cat)}</button>
  `).join('')}</div>`;
}

function setFilter(cat){
  currentFilter = cat;
  renderFilters();
  renderPublic();
}

function renderPublic(){
  const area = document.getElementById('gridArea');
  const visible = items.filter(i => i.see && (currentFilter === 'Tous' || i.category === currentFilter));
  if(visible.length === 0){
    area.innerHTML = `
      <div class="empty-state">
        <div class="big">🎁</div>
        <h3>La liste est vide (pour l'instant)</h3>
        <p>Ajoute des produits dans le fichier products.json pour qu'ils apparaissent ici.</p>
      </div>`;
    return;
  }
  area.innerHTML = `<div class="grid">${visible.map((it, idx) => cardHTML(it, idx)).join('')}</div>`;
}

async function init(){
  try{
    const res = await fetch('products.json');
    const raw = await res.json();
    items = raw.filter(i => i.url && i.url.trim() !== '');
  }catch(e){
    console.error('Impossible de charger products.json', e);
    items = [];
  }
  renderFilters();
  renderPublic();

  for(const it of items){
    if(!it.title || !it.image){
      const preview = await fetchPreview(it.url);
      it.title = it.title || preview.title;
      it.image = it.image || preview.image;
      it.publisher = it.publisher || preview.publisher;
      if((!it.infos || it.infos.length === 0) && preview.infos && preview.infos.length){
        it.infos = preview.infos;
      }
      renderPublic();
    }
  }
}

init();
