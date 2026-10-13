'use strict';
const $ = id => document.getElementById(id);
const text = (tag, value, className) => {
  const el = document.createElement(tag);
  el.textContent = value;
  if (className) el.className = className;
  return el;
};
const number = n => n.toLocaleString();
const filterIds = ['search', 'library', 'status', 'leaf', 'length', 'content', 'trait'];
const traitNames = {brief:'Very brief (under 0.25 s)', tonal_dominant:'Strong tonal component', broadband_noisy:'Broadband noise component', dominant_frequency_moves:'Changing dominant frequency'};
let rows = [], ucs = [], filtered = [], category = '', page = 0;
const pageSize = 50;

function option(select, value, label) {
  const el = text('option', label);
  el.value = value;
  select.append(el);
}
function filters() {
  return {category, query: $('search').value, library: $('library').value,
    status: $('status').value, leaf: $('leaf').value, length: $('length').value,
    content: $('content').value, trait: $('trait').value, showDuplicates: $('duplicates').checked};
}
function clearOtherFilters() {
  for (const id of filterIds) $(id).value = '';
  page = 0;
  applyFilters();
}
function showAllUnclassified() {
  category = 'Unclassified';
  $('duplicates').checked = true;
  updateLeaves();
  clearOtherFilters();
}
function updateStats() {
  $('stats').replaceChildren();
  const counts = [
    [new Set(rows.map(r => r.path)).size, 'audio files'],
    [new Set(rows.map(r => r.duplicate_of || r.path)).size, 'after exact duplicate checks'],
    [new Set(rows.filter(r => r.catid).map(r => r.catid)).size, 'UCS leaves proposed'],
    [rows.filter(r => !r.category).length, 'unclassified entries — view all'],
    [rows.filter(r => r.classification_method === 'audio-model').length, 'audio suggestions awaiting review'],
    [rows.filter(r => r.classification_status === 'source element').length, 'raw samples — need finer labels'],
    [rows.filter(r => r.classification_status === 'context only').length, 'context grouped — event unknown'],
    [rows.filter(r => r.classification_status === 'tentative proposal').length, 'tentative guesses — need listening'],
  ];
  counts.forEach(([count, label], index) => {
    const item = text('div', '', 'stat');
    if (index === 3) {
      const button = text('button', number(count), 'stat-link');
      button.setAttribute('aria-label', 'View all unclassified entries');
      button.onclick = showAllUnclassified;
      item.append(button);
    } else item.append(text('strong', number(count)));
    item.append(text('span', label));
    $('stats').append(item);
  });
}
function duration(value) {
  if (value == null) return 'Unknown duration';
  if (value < 60) return `${value.toFixed(2)} s`;
  const rounded = Math.round(value);
  return `${Math.floor(rounded / 60)}m ${rounded % 60}s`;
}
function updateLeaves() {
  $('leaf').replaceChildren();
  option($('leaf'), '', 'All subcategories');
  ucs.filter(u => !category || u.category === category).forEach(u => option($('leaf'), u.catid, `${u.category} / ${u.subcategory}`));
}
function chooseCategory(value) {
  category = value;
  page = 0;
  updateLeaves();
  applyFilters();
}
function renderCategories() {
  const counts = CatalogueView.categoryCounts(rows, filters());
  $('categories').replaceChildren();
  for (const name of ['Unclassified', ...new Set(ucs.map(u => u.category))]) {
    const button = text('button', name, 'category' + (category === name ? ' active' : ''));
    button.title = 'Matching recordings with a description in this category';
    button.append(text('span', number(counts.get(name) || 0)));
    button.onclick = () => chooseCategory(name);
    $('categories').append(button);
  }
  $('allCategories').classList.toggle('active', !category);
}
function renderActiveFilters() {
  const parts = [];
  if ($('search').value.trim()) parts.push(`Search: “${$('search').value.trim()}”`);
  for (const [id, label] of [['library','Library'], ['status','Classification'], ['leaf','Subcategory'], ['length','Duration'], ['content','Content'], ['trait','Measured character']]) {
    if ($(id).value) parts.push(`${label}: ${$(id).selectedOptions[0].textContent}`);
  }
  $('activeFilters').textContent = `${category || 'All categories'} — ${parts.length ? parts.join(' · ') : 'no additional filters'}`;
  $('clearFilters').disabled = parts.length === 0;
}
function applyFilters() {
  filtered = CatalogueView.filterRows(rows, filters());
  const view = CatalogueView.paginate(filtered, page, pageSize);
  page = view.page;
  renderCategories();
  renderActiveFilters();
  render(view);
}
function play(row) {
  $('playerDock').style.display = 'flex';
  $('now').textContent = row.description;
  $('audio').src = '/audio/' + row.id;
  $('audio').play().catch(() => { $('now').textContent = 'Press play to listen: ' + row.description; });
}
function review(row, card) {
  const existing = card.querySelector('.review');
  if (existing) { existing.remove(); return; }
  const box = text('div', '', 'review');
  const select = document.createElement('select');
  select.setAttribute('aria-label', 'Choose UCS category');
  option(select, '', 'Unclassified / clear label');
  ucs.forEach(u => option(select, u.catid, `${u.category} / ${u.subcategory} (${u.catid})`));
  select.value = row.catid || '';
  const save = text('button', 'Save review');
  const cancel = text('button', 'Cancel');
  save.onclick = async () => {
    save.disabled = true;
    try {
      const response = await fetch('/api/review', {method:'POST', headers:{'Content-Type':'application/json','X-Catalogue-Token':token}, body:JSON.stringify({id:row.id,catid:select.value || null})});
      if (!response.ok) throw new Error((await response.json()).error || 'Could not save');
      const selected = ucs.find(u => u.catid === select.value);
      Object.assign(row, {catid:selected?.catid || null,category:selected?.category || null,subcategory:selected?.subcategory || null,
        classification_status:selected ? 'reviewed' : 'unclassified',reviewed:true,reason:'Manual review in local catalogue'});
      row.search = [row.description,row.path,row.category,row.subcategory,row.catid].join(' ').toLowerCase();
      updateStats();
      applyFilters();
    } catch(error) {
      save.textContent = error.message;
      save.disabled = false;
    }
  };
  cancel.onclick = () => box.remove();
  box.append(select,save,cancel);
  card.append(box);
}
function render(view = CatalogueView.paginate(filtered, page, pageSize)) {
  page = view.page;
  $('count').textContent = view.total
    ? `Showing ${number(view.first)}–${number(view.last)} of ${number(view.total)} matching description entries · ${number(new Set(filtered.map(r => r.path)).size)} recordings`
    : 'No matching entries';
  $('results').replaceChildren();
  for (const row of view.items) {
    const card = text('article','','card');
    const body = document.createElement('div');
    body.append(text('div',row.description,'title'));
    body.append(text('span',row.catid ? `${row.category} / ${row.subcategory}` : row.category || 'Unclassified','tag' + (!row.catid ? ' uncertain' : '')));
    body.append(text('span',row.classification_status === 'provisional' ? `Proposed · ${row.confidence || 'unknown'} metadata confidence` : row.classification_status,'tag uncertain'));
    if (row.classification_method === 'audio-model') body.append(text('span','Audio model suggestion · needs review','tag uncertain'));
    if (row.classification_method === 'exact-excerpt') body.append(text('span','Exact sample excerpt match · needs review','tag uncertain'));
    if (row.classification_status === 'source element') body.append(text('span','Raw sample · needs a finer sound label','tag uncertain'));
    if (row.classification_status === 'context only') body.append(text('span','Source context known · sound event unresolved','tag uncertain'));
    if (row.classification_status === 'tentative proposal') body.append(text('span','Tentative category guess · conflicting or weak evidence','tag uncertain'));
    for (const trait of row.acoustic_traits || []) body.append(text('span',traitNames[trait] || trait,'tag'));
    if (row.duplicate_of) body.append(text('span','Duplicate','tag uncertain'));
    body.append(text('div',`${row.library} · ${duration(row.duration)} · ${row.sample_rate ? number(row.sample_rate) + ' Hz' : ''} · ${row.content || 'unknown'}`,'meta'));
    body.append(text('div',row.reason || 'No classification recorded yet.','reason'));
    const proposed = (row.extra?.proposed_catids || []).map(id => ucs.find(u => u.catid === id)).filter(Boolean);
    if (proposed.length) body.append(text('div','Named sources: ' + proposed.map(u => `${u.category} / ${u.subcategory}`).join('; ') + '. Separate events still need locating.','reason'));
    const details = document.createElement('details');
    details.append(text('summary','Source and classification evidence'));
    details.append(text('div',row.path,'meta'));
    if (row.original_category) details.append(text('div','Original category: ' + row.original_category,'meta'));
    if (row.metadata_source) details.append(text('div','Metadata: ' + row.metadata_source,'meta'));
    const automatic = row.extra?.automated_proposal;
    if (automatic?.alternatives?.length) details.append(text('div','Other audio matches: ' + automatic.alternatives.map(value => value.catid || value.category || value.label).filter(Boolean).join(', '),'meta'));
    const audioModel = automatic?.model || automatic?.evidence?.qwen_model;
    if (audioModel) details.append(text('div','Audio model: ' + (audioModel.name || audioModel) + '. Similarity scores are not probabilities.','meta'));
    if (automatic?.modelcaption) details.append(text('div','Model description (unverified): ' + automatic.modelcaption,'meta'));
    const audioReferences = automatic?.evidence?.acoustic_neighbour_references;
    if (audioReferences?.length) details.append(text('div','Nearest labelled recordings: ' + audioReferences.slice(0,3).map(value => `${value.description || value.path} (${value.category})`).join('; '),'meta'));
    if (row.extra?.waveform_measurements) details.append(text('div','Character tags are measured waveform properties. They do not identify a sound source or prove synthesis.','meta'));
    if (row.extra?.expected_duration) details.append(text('div','Guide entry duration: ' + row.extra.expected_duration + ' s (boundaries not verified)','meta'));
    body.append(details);
    const actions = text('div','','actions');
    const playButton = text('button','▶ Play');
    const reviewButton = text('button','Review');
    playButton.onclick = () => play(row);
    reviewButton.onclick = () => review(row,card);
    actions.append(playButton,reviewButton);
    card.append(body,actions);
    $('results').append(card);
  }
  if (!view.total) $('results').append(text('div','No recordings match these filters. Use “Clear other filters” to broaden this category.','empty'));
  document.querySelectorAll('.page-label').forEach(el => { el.textContent = view.totalPages ? `Page ${view.page + 1} of ${view.totalPages}` : 'No pages'; });
  document.querySelectorAll('.previous-page').forEach(el => { el.disabled = !view.canPrevious; });
  document.querySelectorAll('.next-page').forEach(el => { el.disabled = !view.canNext; });
  $('pageJump').value = view.totalPages ? view.page + 1 : 0;
  $('pageJump').max = view.totalPages;
  $('pageJump').disabled = !view.totalPages;
}
function movePage(value) {
  page = value;
  render();
  document.querySelector('main').scrollIntoView({block:'start'});
}
async function init() {
  try {
    const responses = await Promise.all(['/api/records','/api/ucs','/api/summary'].map(path => fetch(path).then(response => {
      if (!response.ok) throw new Error('Catalogue could not be loaded');
      return response.json();
    })));
    [rows, ucs] = responses;
    const summary = responses[2];
    rows.forEach(row => { row.search = [row.description,row.path,row.category,row.subcategory,row.catid].join(' ').toLowerCase(); });
    const statusCount = name => summary.statuses.find(value => value.status === name)?.files || 0;
    $('inventoryStatus').textContent = `${summary.libraries.length} libraries with playable audio. ${number(statusCount('needs_extracting'))} archive or installer files await extraction; ${number(statusCount('unrecognised'))} legacy files are not recognised by the decoder; ${number(statusCount('pending'))} files could not yet be read as audio. Originals are preserved. Labels include metadata and provisional audio suggestions; event segmentation and listening verification are still to come. Counts reflect the last inventory run.`;
    [...new Set(rows.map(row => row.library))].sort().forEach(library => option($('library'),library,library));
    Object.entries(traitNames).forEach(([value,label]) => option($('trait'),value,label));
    updateStats();
    updateLeaves();
    applyFilters();
  } catch(error) {
    $('stats').textContent = error.message;
    $('stats').className = 'error';
  }
}
for (const id of filterIds) $(id).addEventListener(id === 'search' ? 'input' : 'change', () => {page = 0; applyFilters();});
$('duplicates').onchange = () => {page = 0; applyFilters();};
$('allCategories').onclick = () => chooseCategory('');
$('clearFilters').onclick = clearOtherFilters;
document.querySelectorAll('.previous-page').forEach(el => { el.onclick = () => movePage(page - 1); });
document.querySelectorAll('.next-page').forEach(el => { el.onclick = () => movePage(page + 1); });
$('pageJump').onchange = () => movePage(Number($('pageJump').value) - 1);
$('pageJump').onkeydown = event => { if (event.key === 'Enter') movePage(Number($('pageJump').value) - 1); };
$('audio').onerror = () => { $('now').textContent = 'Playback failed. This recording may need a fresh scan or a different decoder.'; };
init();
