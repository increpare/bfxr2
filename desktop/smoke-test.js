const { _electron: electron } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
require('./build');
const artifacts = path.join(__dirname, 'artifacts');
fs.mkdirSync(artifacts, { recursive: true });
const env = { ...process.env, BFXR_TEST_PROFILE: path.join(artifacts, 'profile-' + Date.now()) };
const unique = Date.now();
delete env.ELECTRON_RUN_AS_NODE;
const report = { scales: [], errors: [] };
const delay = ms => new Promise(resolve => setTimeout(resolve,ms));
async function savedFile(file) {
  for (let i=0;i<150;i++) { if(fs.existsSync(file) && fs.statSync(file).size>0) return; await delay(100); }
  throw new Error('Timed out saving '+file);
}

async function launch(scale = 1) {
  const start = Date.now();
  const packaged = process.env.BFXR_PACKAGED === '1';
  const app = await electron.launch({ ...(packaged ? {executablePath:path.join(__dirname,'../dist/Bfxr95/Bfxr.exe')} : {}), args: [...(packaged ? [] : [path.join(__dirname, 'main.js')]), '--force-device-scale-factor=' + scale], env });
  const page = await app.firstWindow();
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => report.errors.push(error.message));
  await page.waitForSelector('#status95');
  await page.evaluate(() => document.fonts.ready);
  report.launches ||= [];
  report.launches.push({scale, packaged, millisecondsToUsable:Date.now()-start});
  return { app, page };
}
(async () => {
  let app;
  try {
    let session = await launch(); app = session.app; const page = session.page;
    report.runtime = await app.evaluate(({ app, BrowserWindow }) => ({ electron:process.versions.electron, grayscale:app.commandLine.hasSwitch('disable-lcd-text'), gpu:app.getGPUFeatureStatus(), sandbox:BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences().sandbox }));
    assert.equal(report.runtime.grayscale,true); assert.equal(report.runtime.sandbox,true);
    assert.equal(await page.locator('[role=tab]').count(),23);
    await page.locator('#Bfxr_generator_generate_pickup_coin').click();
    const count = await page.evaluate(() => active95().files.length);
    await page.getByRole('button',{name:'Mutate',exact:true}).first().click();
    assert.equal(await page.evaluate(() => active95().files.length),count+1);
    await page.locator('#tab_button_Bfxr').focus();
    await page.keyboard.press('Alt+f');
    assert.equal(await page.locator('#menu95-0').isVisible(),true);
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#menu95-1').isVisible(),true);
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(() => document.activeElement.id),'tab_button_Bfxr');
    const lock = page.locator('.active_tab_page .lockimage').first();
    await lock.focus(); const before = await lock.getAttribute('aria-pressed');
    await page.keyboard.press('Space'); assert.notEqual(await lock.getAttribute('aria-pressed'),before);
    await page.keyboard.press('Space');
    await page.locator('.active_tab_page [role=slider]').first().focus();
    const sliderBefore = await page.locator('.active_tab_page [role=slider]').first().getAttribute('aria-valuenow');
    await page.keyboard.press('ArrowRight');
    assert.notEqual(await page.locator('.active_tab_page [role=slider]').first().getAttribute('aria-valuenow'),sliderBefore);
    // Exercise the real engine, download pipeline and native file chooser import.
    const wav = path.join(artifacts,`export-${unique}.wav`);
    await app.evaluate(({ BrowserWindow }, target) => BrowserWindow.getAllWindows()[0].webContents.session.once('will-download', (_event,item) => item.setSavePath(target)), wav);
    await page.getByRole('button',{name:'Export WAV',exact:true}).first().click();
    await savedFile(wav);
    assert.equal(fs.readFileSync(wav).subarray(0,4).toString(),'RIFF');
    const sound = path.join(artifacts,`saved-${unique}.bfxr`);
    await app.evaluate(({ BrowserWindow }, target) => BrowserWindow.getAllWindows()[0].webContents.session.once('will-download', (_event,item) => item.setSavePath(target)), sound);
    await page.getByRole('button',{name:'Save',exact:true}).click(); await savedFile(sound);
    const soundData = JSON.parse(fs.readFileSync(sound,'utf8')); assert.equal(soundData.synth_type,'Bfxr');
    const chooser = page.waitForEvent('filechooser'); await page.getByRole('button',{name:'Open...',exact:true}).last().click();
    await (await chooser).setFiles(sound);
    await page.waitForFunction(count => active95().files.length === count+1, count+1);
    const names = await page.evaluate(() => tabs.map(tab => tab.name));
    report.generators = [];
    for (const name of names) {
      await page.locator('#tab_button_' + name).click();
      const result = await page.evaluate(() => { const tab = active95(); tab.synth.generate_sound(); return { name:tab.name, uri:tab.synth.generate_sound_uri().slice(0,30), controls:document.querySelectorAll('.active_tab_page button').length }; });
      assert.match(result.uri,/^data:audio/); report.generators.push(result);
      if (['Jinglr','Transfxr','Mixr'].includes(name)) await page.screenshot({path:path.join(artifacts,name+'.png')});
    }
    // Empty collections must remain usable, including bulk export.
    await page.evaluate(()=> { const tab=active95(); for(const file of [...tab.files]) tab.delete_file(file[0]); });
    assert.equal(await page.getByRole('button',{name:'Save',exact:true}).isDisabled(),true);
    await page.locator('#tab_button_Bfxr').click();
    const paramsBeforeExport = await page.evaluate(()=>JSON.stringify(active95().synth.params));
    await page.locator('.active_tab_page [id="export_all"]').click();
    await page.locator('#export-download-link').waitFor({state:'visible'});
    assert.equal(await page.evaluate(()=>JSON.stringify(active95().synth.params)),paramsBeforeExport);
    const zip = path.join(artifacts,`collection-${unique}.zip`);
    await app.evaluate(({ BrowserWindow }, target) => BrowserWindow.getAllWindows()[0].webContents.session.once('will-download', (_event,item) => item.setSavePath(target)), zip);
    await page.locator('#export-download-link').click(); await savedFile(zip);
    assert.equal(fs.readFileSync(zip).subarray(0,2).toString(),'PK');
    await page.keyboard.press('Escape');
    await page.keyboard.press('F1');
    await page.locator('#about-dialog[open]').waitFor();
    await page.screenshot({path:path.join(artifacts,'about.png')});
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#about-dialog').isVisible(),false);
    await page.screenshot({path:path.join(artifacts,'desktop-100.png')});
    // Native window state and constrained layout.
    await page.getByRole('button',{name:'Maximize',exact:true}).click();
    await page.getByRole('button',{name:'Restore window'}).waitFor();
    assert.equal(await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].isMaximized()),true);
    await page.getByRole('button',{name:'Restore window'}).click();
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(760,560));
    await page.screenshot({path:path.join(artifacts,'desktop-narrow.png')});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.getByRole('button',{name:'Minimize',exact:true}).click();
    assert.equal(await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].isMinimized()),true);
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].restore());
    const persisted = await page.evaluate(()=>active95().files.length);
    await app.close(); app = null;
    for (const scale of [1.25,1.5,2]) {
      session = await launch(scale); app = session.app;
      assert.equal(await session.page.evaluate(()=>active95().files.length),persisted);
      await session.page.screenshot({path:path.join(artifacts,`desktop-${scale*100}.png`)});
      report.scales.push({scale, dpr:await session.page.evaluate(()=>devicePixelRatio),overflow:await session.page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
      await app.close(); app = null;
    }
    assert.deepEqual(report.errors,[]);
    fs.writeFileSync(path.join(artifacts,'report.json'),JSON.stringify(report,null,2));
    console.log('Passed: 23 generators, audio/WAV, save/open, persistence, menus, keyboard controls, native window controls, narrow layout and four display scales.');
  } finally { if(app) await app.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
