const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function deleteSound(selected, deleted, playOnChange = true) {
    const api = createContext();
    api.load('js/Tab.js');
    return plain(api.run(`(() => {
        let applied = 0, generated = 0, drawn = 0, played = 0, saved = 0;
        const files = ['A', 'B', 'C'].map((name, value) => [name, JSON.stringify({value}), '{}']);
        const tab = Object.create(Tab.prototype);
        Object.assign(tab, {
            files, selected_file_index: ${selected}, play_on_change: ${playOnChange},
            synth: {apply_params(){applied++;}, generate_sound(){generated++;}},
            redraw_waveform(){drawn++;}, play_sound(){played++;}, update_ui(){}
        });
        globalThis.SaveLoad = {save_all_collections(){saved++;}};
        tab.delete_file('${deleted}');
        return {selected:tab.selected_file_index, name:tab.files[tab.selected_file_index]?.[0],
            applied, generated, drawn, played, saved};
    })()`));
}

test('deleting another sound does not replay or reload the selection', () => {
    assert.deepEqual(deleteSound(1, 'A'),
        {selected:0, name:'B', applied:0, generated:0, drawn:0, played:0, saved:1});
    assert.deepEqual(deleteSound(1, 'C'),
        {selected:1, name:'B', applied:0, generated:0, drawn:0, played:0, saved:1});
});

test('deleting the selected sound previews its replacement when enabled', () => {
    assert.deepEqual(deleteSound(1, 'B'),
        {selected:0, name:'A', applied:1, generated:1, drawn:1, played:1, saved:1});
    assert.deepEqual(deleteSound(0, 'A'),
        {selected:0, name:'B', applied:1, generated:1, drawn:1, played:1, saved:1});
    assert.deepEqual(deleteSound(1, 'B', false),
        {selected:0, name:'A', applied:1, generated:1, drawn:1, played:0, saved:1});
});

test('deleting the final selected sound has nothing to preview', () => {
    const api = createContext();
    api.load('js/Tab.js');
    assert.deepEqual(plain(api.run(`(() => {
        let played = 0;
        const tab = Object.create(Tab.prototype);
        Object.assign(tab, {files:[['Only', '{}', '{}']], selected_file_index:0, play_on_change:true,
            play_sound(){played++;}, update_ui(){}, synth:{}});
        globalThis.SaveLoad = {save_all_collections(){}};
        tab.delete_file('Only');
        return {selected:tab.selected_file_index, count:tab.files.length, played};
    })()`)), {selected:-1, count:0, played:0});
});
