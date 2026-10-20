/* Desktop-only adaptation. The web app and synthesis engines stay shared. */
'use strict';
const active95 = () => tabs.find(tab => tab.active);
const originalKey95 = Tab.prototype.on_key_down;
Tab.prototype.on_key_down = function(event) {
  if (document.querySelector('dialog[open]') || event.target.closest('[role=button],[role=tab],.menubar95')) return;
  return originalKey95.call(this,event);
};
// Render a snapshot for bulk export, including collections with empty synths.
// Always restore the live synth after rendering each stored sound.
Tab.prototype.export_all_button_clicked = async function() {
  const dialog = document.getElementById('export-dialog');
  const link = document.getElementById('export-download-link');
  const progress = document.getElementById('export-progress');
  const message = document.getElementById('export-progress-text');
  const sounds = tabs.flatMap(tab => tab.files.map(file => ({ tab, name:file[0], params:JSON.parse(file[1]) })));
  const zip = new JSZip();
  if (link.href.startsWith('blob:')) URL.revokeObjectURL(link.href);
  link.style.display = 'none'; progress.max = Math.max(1,sounds.length); progress.value = 0;
  message.textContent = 'Preparing sounds...'; dialog.showModal();
  try {
    for (const sound of sounds) {
      if (!dialog.open) return;
      const synth = sound.tab.synth, params = structuredClone(synth.params), preview = synth.sound, soundParams = synth.sound_params;
      try {
        synth.apply_params(sound.params);
        zip.folder(sound.tab.name).file(sound.name+'.wav',synth.generate_sound_uri().split(',')[1],{base64:true});
      } finally { synth.apply_params(params); synth.sound = preview; synth.sound_params = soundParams; }
      progress.value++;
      message.textContent = `${progress.value}/${sounds.length} sounds generated`;
      await new Promise(resolve => setTimeout(resolve,0));
    }
    const archive = await zip.generateAsync({type:'blob'});
    if (!dialog.open) return;
    link.href = URL.createObjectURL(archive); link.style.display = 'block';
    progress.value = progress.max; message.textContent = 'Your WAV collection is ready.';
  } catch (error) { message.textContent = 'Export failed: '+error.message; }
};
const glyph95 = paths => `<svg viewBox="0 0 16 16" aria-hidden="true">${paths}</svg>`;
const icons95 = {
  open: glyph95('<path fill="#808080" stroke="#000" d="M1 3h5l2 2h6v8H1z"/><path fill="#fff" stroke="#000" d="M3 7h12l-3 7H1z"/>'),
  save: glyph95('<path fill="#c0c0c0" stroke="#000" d="M1 1h12l2 2v12H1z"/><path fill="#fff" stroke="#000" d="M4 1h7v5H4zM4 9h8v6H4z"/><path d="M9 2h1v3H9z"/>'),
  play: glyph95('<path d="M4 2l10 6-10 6z"/>'),
  export: glyph95('<path fill="#fff" stroke="#000" d="M3 1h7l3 3v11H3z"/><path d="M5 9h2V6h2v3h2l-3 4z"/>'),
  mutate: glyph95('<path fill="#fff" stroke="#000" d="M2 2h12v12H2z"/><path d="M4 4h2v2H4zM10 4h2v2h-2zM7 7h2v2H7zM4 10h2v2H4zM10 10h2v2h-2z"/>')
};
document.addEventListener('DOMContentLoaded', () => {
  const shell = document.createElement('header');
  shell.innerHTML = `<div class="caption95"><span class="app-icon">${glyph95('<path fill="#fff" stroke="#000" d="M1 1h14v14H1z"/><path stroke="#000" fill="none" d="M2 8h2l2-5 3 10 2-5h3"/>')}</span><strong>Bfxr — Sound Effects</strong>
    <div class="gui95-caption-controls"><button type="button" class="gui95-caption-button" data-caption-icon="minimize" aria-label="Minimize" data-window="minimize"></button>
    <button type="button" class="gui95-caption-button" data-caption-icon="maximize" aria-label="Maximize" data-window="maximize"></button>
    <button type="button" class="gui95-caption-button" data-caption-icon="close" aria-label="Close window" data-window="close"></button></div></div>
    <nav class="menubar95" aria-label="Application menu" role="menubar"></nav>
    <div class="toolbar95" role="toolbar" aria-label="Sound commands">
      <button data-command="open">${icons95.open}Open...</button><button data-command="save">${icons95.save}Save</button>
      <i class="separator95"></i><button data-command="play">${icons95.play}Play</button><button data-command="mutate">${icons95.mutate}Mutate</button>
      <i class="separator95"></i><button data-command="export">${icons95.export}Export WAV</button><span class="toolbar-note">Sound effects for your games</span>
    </div>`;
  document.body.prepend(shell);
  const status = document.createElement('footer');
  status.className = 'status95';
  status.innerHTML = '<span id="status95" role="status">Ready.</span><span id="count95"></span><span>44,100 Hz · Mono</span>';
  document.body.append(status);
  const setStatus = text => document.getElementById('status95').textContent = text;
  const invoke = (method) => { const tab = active95(); if (tab) tab[method](); };
  const commands = {
    open: () => invoke('open_data_button_clicked'), save: () => invoke('save_bfxr_button_clicked'),
    collection: () => invoke('save_bfxrcol_button_clicked'), export: () => invoke('export_wav_button_clicked'),
    exportAll: () => invoke('export_all_button_clicked'), play: () => invoke('play_button_clicked'),
    copy: () => invoke('copy_button_clicked'), paste: () => invoke('paste_button_clicked'),
    duplicate: () => invoke('duplicate_sfx'), revert: () => invoke('revert_sfx'),
    lock: () => invoke('toggle_all_locks'), random: () => generate('randomize_params'),
    mutate: () => generate('mutate_params'), about: () => invoke('about_button_clicked'),
    exit: () => window.bfxrDesktop?.windowCommand('close')
  };
  function generate(name) {
    const tab = active95();
    if (tab?.synth.templates.some(template => template[2] === name)) tab.template_clicked(name);
  }
  function execute(name) {
    if (shell.querySelector(`[data-command="${name}"]`)?.disabled) return;
    try { commands[name]?.(); refresh(); }
    catch (error) { setStatus('Could not complete this command: ' + error.message); }
  }
  const menus = [
    ['File', [['Open...','Ctrl+O','open'],['Save sound...','Ctrl+S','save'],['Save collection...','','collection'],null,['Export WAV...','Ctrl+E','export'],['Export all sounds...','','exportAll'],null,['Exit','Alt+F4','exit']]],
    ['Edit', [['Copy sound','Ctrl+C','copy'],['Paste sound','Ctrl+V','paste'],null,['Duplicate sound','','duplicate'],['Revert changes','','revert']]],
    ['Sound', [['Play','Space','play'],['Randomize','R','random'],['Mutate','M','mutate'],null,['Lock / unlock parameters','L','lock']]],
    ['Help', [['About Bfxr / Shortcuts','F1','about']]]
  ];
  let opened = null, previousFocus = null;
  const menubar = shell.querySelector('.menubar95');
  menus.forEach(([label, items], index) => {
    const menu = document.createElement('div');
    menu.className = 'menu95';
    menu.innerHTML = `<button role="menuitem" aria-haspopup="menu" aria-expanded="false" aria-controls="menu95-${index}"><u>${label[0]}</u>${label.slice(1)}</button><div class="popup95" id="menu95-${index}" role="menu" aria-label="${label}" hidden></div>`;
    for (const item of items) {
      if (!item) { menu.lastChild.append(document.createElement('hr')); continue; }
      const button = document.createElement('button');
      button.role = 'menuitem'; button.dataset.command = item[2];
      button.innerHTML = `<span>${item[0]}</span><span>${item[1]}</span>`;
      menu.lastChild.append(button);
    }
    menu.firstChild.addEventListener('click', () => opened === menu ? closeMenu() : openMenu(menu));
    menu.firstChild.addEventListener('pointerenter', () => { if (opened && opened !== menu) openMenu(menu); });
    menubar.append(menu);
  });
  function closeMenu(restore = true) {
    if (!opened) return;
    opened.firstChild.setAttribute('aria-expanded','false'); opened.lastChild.hidden = true; opened = null;
    if (restore) previousFocus?.focus();
  }
  function openMenu(menu) {
    if (!opened) previousFocus = document.activeElement;
    closeMenu(false); opened = menu;
    refresh();
    menu.firstChild.setAttribute('aria-expanded','true'); menu.lastChild.hidden = false;
    menu.querySelector('.popup95 button:not(:disabled)')?.focus();
  }
  shell.addEventListener('click', event => {
    const command = event.target.closest('[data-command]');
    if (command) { closeMenu(); execute(command.dataset.command); }
    const control = event.target.closest('[data-window]');
    if (control) window.bfxrDesktop?.windowCommand(control.dataset.window);
  });
  document.addEventListener('pointerdown', event => { if (!event.target.closest('.menubar95')) closeMenu(false); });
  document.addEventListener('keydown', event => {
    const editing = event.target.closest('input,textarea,select,[contenteditable=true]');
    const modal = document.querySelector('dialog[open]');
    if (modal) { event.stopImmediatePropagation(); return; }
    if (opened) {
      event.stopImmediatePropagation();
      const items = [...opened.querySelectorAll('.popup95 button:not(:disabled)')];
      let index = items.indexOf(document.activeElement);
      if (event.key === 'Escape' || event.key === 'F10') closeMenu();
      else if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        index = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
        items[index]?.focus();
      } else if (['ArrowLeft','ArrowRight'].includes(event.key)) {
        const all = [...menubar.children]; openMenu(all[(all.indexOf(opened) + (event.key === 'ArrowRight' ? 1 : -1) + all.length) % all.length]);
      } else if (event.key === 'Enter' || event.key === ' ') document.activeElement.click();
      else if (event.key.length === 1) items.find(item => item.textContent.toLowerCase().startsWith(event.key.toLowerCase()))?.focus();
      event.preventDefault(); return;
    }
    const menuIndex = event.altKey ? menus.findIndex(([name]) => name[0].toLowerCase() === event.key.toLowerCase()) : -1;
    if (menuIndex >= 0 || event.key === 'F10') {
      event.preventDefault(); event.stopImmediatePropagation(); openMenu(menubar.children[Math.max(0,menuIndex)]); return;
    }
    if (editing) return;
    const key = event.key.toLowerCase(), modifier = event.ctrlKey || event.metaKey;
    const command = modifier ? ({o:'open',s:'save',e:'export',c:'copy',v:'paste'})[key] : ({r:'random',m:'mutate',l:'lock',f1:'about'})[key];
    if (command) { event.preventDefault(); event.stopImmediatePropagation(); execute(command); }
  }, true);

  const tabbar = document.getElementById('tab_bar');
  tabbar.role = 'tablist'; tabbar.setAttribute('aria-label','Sound generators'); tabbar.setAttribute('aria-orientation','horizontal');
  const generatorButtons = tabs.map(tab => document.getElementById('tab_button_' + tab.name));
  let rowCount = 0;
  function layoutTabs() {
    const count = Math.ceil(tabs.length / Math.max(1,Math.floor((tabbar.clientWidth-4)/84)));
    if (count !== rowCount) {
      const focused = tabbar.contains(document.activeElement) ? document.activeElement : null;
      rowCount = count;
      const perRow = Math.ceil(tabs.length/count), rows = [];
      for (let i=0;i<tabs.length;i+=perRow) {
        const row = document.createElement('div'); row.className = 'tab-row95'; row.role = 'presentation';
        row.append(...generatorButtons.slice(i,i+perRow)); rows.push(row);
      }
      tabbar.replaceChildren(...rows);
      focused?.focus({preventScroll:true});
    }
    // Classic multiline tab controls bring the selected row against its page.
    [...tabbar.children].forEach((row,index) => row.style.order = row.querySelector('.active_tab') ? rowCount : index);
  }
  new ResizeObserver(layoutTabs).observe(tabbar);
  for (const tab of tabs) {
    const button = document.getElementById('tab_button_' + tab.name);
    button.role = 'tab'; button.setAttribute('aria-controls','tab_page_' + tab.name);
    const page = document.getElementById('tab_page_' + tab.name);
    page.role = 'tabpanel'; page.setAttribute('aria-labelledby',button.id);
    button.addEventListener('keydown', event => {
      if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)) {
        event.preventDefault();
        const at = tabs.indexOf(tab);
        let next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (at + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
        if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
          const rows = [...tabbar.children].sort((a,b) => a.getBoundingClientRect().top-b.getBoundingClientRect().top);
          const row = rows[(rows.indexOf(button.parentElement)+(event.key === 'ArrowDown' ? 1 : -1)+rows.length)%rows.length];
          const center = node => { const box=node.getBoundingClientRect(); return box.left+box.width/2; };
          const nearest = [...row.children].sort((a,b)=>Math.abs(center(a)-center(button))-Math.abs(center(b)-center(button)))[0];
          next = generatorButtons.indexOf(nearest);
        }
        tabs[next].set_active_tab(true); document.getElementById('tab_button_' + tabs[next].name).focus();
      } else if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); tab.set_active_tab(true); }
    });
  }
  // Add keyboard semantics to the shared app's pointer-only lock widgets.
  function decorate(tab) {
    if (!tab.ui_initialized) return;
    const page = document.getElementById('tab_page_' + tab.name);
    if (!page.dataset.decorated95) {
      page.dataset.decorated95 = 'true';
      for (const [selector, text] of [['.centre_panel','Sound parameters'],['.right_panel','Waveform'],['.filelist','Sound collection']]) {
        const label = document.createElement('h2'); label.className = 'pane-label95'; label.textContent = text;
        const node = page.querySelector(selector); selector === '.filelist' ? node.before(label) : node.prepend(label);
      }
      page.querySelector('[id="copy_link"]').hidden = true;
      // Sharing a file:// URL is meaningless outside this desktop app.
      for (const [name, lock] of Object.entries(tab.lock_buttons)) {
        lock.role = 'button'; lock.tabIndex = 0; lock.setAttribute('aria-label','Lock ' + name);
        lock.addEventListener('keydown', event => { if (event.key === ' ' || event.key === 'Enter') { event.preventDefault(); lock.click(); } });
      }
      for (const [name, slider] of Object.entries(tab.sliders)) {
        for (const handle of slider.sliderElem.querySelectorAll('[role=slider]')) handle.setAttribute('aria-label', name);
      }
    }
    for (const [name, lock] of Object.entries(tab.lock_buttons)) lock.setAttribute('aria-pressed',String(!!tab.synth.locked_params[name]));
  }
  function refresh() {
    const tab = active95(); if (!tab) return;
    for (const item of tabs) {
      const button = document.getElementById('tab_button_' + item.name);
      button.setAttribute('aria-selected',String(item.active)); button.tabIndex = item.active ? 0 : -1;
    }
    layoutTabs();
    decorate(tab);
    document.getElementById('count95').textContent = `${tab.files.length} sound${tab.files.length === 1 ? '' : 's'}`;
    const hasSound = tab.selected_file_index >= 0;
    const state = tab.files[tab.selected_file_index];
    const panel = document.getElementById('tab_page_' + tab.name);
    for (const id of ['save_bfxr','export_wav','copy','play',tab.name+'_duplicate_sfx',tab.name+'_mix_sound']) {
      const button = panel.querySelector(`[id="${id}"]`); if(button) button.disabled = !hasSound;
    }
    for (const id of [tab.name+'_apply_sfx',tab.name+'_revert_sfx']) {
      const button = panel.querySelector(`[id="${id}"]`); if(button) button.disabled = !state || state[1] === state[2];
    }
    for (const button of shell.querySelectorAll('[data-command]')) {
      const name = button.dataset.command;
      button.disabled = ['save','export','copy','duplicate','revert','play','mutate'].includes(name) && !hasSound;
      if (name === 'revert') button.disabled = !state || state[1] === state[2];
      if (name === 'random' || name === 'mutate') button.disabled ||= !tab.synth.templates.some(item => item[2] === (name === 'random' ? 'randomize_params' : 'mutate_params'));
    }
  }
  // Shared methods notify the desktop only after completing their usual behavior.
  for (const name of ['set_active_tab','update_ui','update_ablements','parameter_changed','lock_param_clicked','toggle_all_locks']) {
    const original = Tab.prototype[name];
    Tab.prototype[name] = function(...args) {
      const result = original.apply(this,args); refresh();
      if(name === 'set_active_tab') SaveLoad.save_all_collections();
      return result;
    };
  }
  document.addEventListener('pointerover', event => {
    const title = event.target.closest('[title]')?.title;
    setStatus(title || 'Ready. Select a preset to generate a sound.');
  });
  window.bfxrDesktop?.onWindowState(state => {
    document.body.classList.toggle('inactive95',!state.focused);
    const maximize = shell.querySelector('[data-window=maximize]');
    maximize.dataset.captionIcon = state.maximized ? 'restore' : 'maximize';
    maximize.setAttribute('aria-label',state.maximized ? 'Restore window' : 'Maximize');
    maximize.title = maximize.getAttribute('aria-label');
  });
  window.bfxrDesktop?.onDownload(setStatus);
  refresh();
});
