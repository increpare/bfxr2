// A board of game verbs. Every button is a verb; every press draws a fresh interpretation
// from a weighted catalogue of engine verb presets and Mixfxr pairs. A board sound is a
// Mixr record, so saving, sharing and exporting need nothing new.
class Soundboard extends Mixr {
    name = 'Soundboard';
    tooltip = 'Game sounds by verb. Every press is a fresh take from across the whole suite.';
    canvas_bg_logo = null;
    hide_params = ['masterVolume', 'seed', 'sources', 'balance', 'align', 'offset'];
    static includeRetired = true;
    // Each entry is a single verb preset ('Synth:verb' or 'Synth:generate_x') or a mix of a base
    // and a sweetener. Weights bias the draw; align 0 = start, 1 = peak, 2 = tail.
    static catalogue = {
        jump: [
            {src:'Bfxr:jump', w:4}, {src:'Transfxr:jump', w:4}, {src:'Squishr:jump', w:1}, {src:'Birdr:jump', w:1},
            {mix:['Bfxr:jump','Transfxr:jump'], balance:[0.3,0.45], align:0, w:1}],
        land: [
            {src:'Footsteppr:land', w:2}, {src:'Bouncr:land', w:3}, {src:'Clonkr:land', w:1}, {src:'Boomr:land', w:2}, {src:'Squishr:land', w:1}, {src:'Rustlr:land', w:1}, {src:'Transfxr:land', w:3},
            {mix:['Bouncr:land','Rustlr:land'], balance:[0.35,0.5], align:0, w:2},
            {mix:['Boomr:land','Fractr:step'], balance:[0.3,0.45], align:0, w:1}],
        step: [
            {src:'Footsteppr:step', w:5}, {src:'Clonkr:step', w:1}, {src:'Bouncr:step', w:1}, {src:'Fractr:step', w:1}, {src:'Rustlr:step', w:1}, {src:'Squishr:step', w:1},
            {mix:['Footsteppr:step','Rustlr:step'], balance:[0.3,0.45], align:0, w:2}],
        dash: [
            {src:'Whooshr:dash', w:4}, {src:'Transfxr:dash', w:4}, {src:'Riftr:dash', w:2}, {src:'Breathr:dash', w:1},
            {mix:['Whooshr:dash','Zappr:shoot'], balance:[0.25,0.4], align:0, w:1},
            {mix:['Whooshr:dash','Riftr:dash'], balance:[0.35,0.5], align:1, w:1}],
        splash: [
            {src:'Squishr:splash', w:5}, {src:'Transfxr:splash', w:3}, {src:'Squishr:generate_wet_splat', w:1}, {src:'Squishr:generate_gulp', w:1},
            {mix:['Squishr:splash','Bouncr:land'], balance:[0.45,0.6], align:0, w:1},
            {mix:['Squishr:splash','Squishr:heal'], balance:[0.25,0.4], align:2, w:1}],
        shoot: [
            {src:'Bfxr:shoot', w:5}, {src:'Transfxr:shoot', w:5}, {src:'Zappr:shoot', w:2}, {src:'Whooshr:shoot', w:1}, {src:'Boomr:shoot', w:1}, {src:'Swarmr:shoot', w:1},
            {src:'Pewpr:generate_laser_pistol', w:2}, {src:'Pewpr:generate_shotgun', w:1}, {src:'Pewpr:generate_railgun', w:1},
            {mix:['Bfxr:shoot','Zappr:shoot'], balance:[0.3,0.45], align:0, w:1},
            {mix:['Boomr:shoot','Whooshr:shoot'], balance:[0.35,0.5], align:0, w:1}],
        swing: [
            {src:'Whooshr:swing', w:5}, {src:'Transfxr:swing', w:4}, {src:'Whooshr:generate_heavy_swing', w:1}, {src:'Rustlr:swing', w:1},
            {mix:['Whooshr:swing','Breathr:dash'], balance:[0.25,0.4], align:0, w:1}],
        hit: [
            {src:'Bfxr:hit', w:4}, {src:'Transfxr:hit', w:4}, {src:'Clonkr:hit', w:2}, {src:'Bouncr:hit', w:1}, {src:'Fractr:hit', w:1}, {src:'Boomr:hit', w:1}, {src:'Zappr:hit', w:1},
            {mix:['Clonkr:hit','Zappr:hit'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Boomr:hit','Fractr:hit'], balance:[0.3,0.45], align:0, w:1},
            {mix:['Bfxr:hit','Clonkr:hit'], balance:[0.35,0.5], align:0, w:1}],
        hurt: [
            {src:'Bfxr:hurt', w:4}, {src:'Transfxr:hurt', w:4}, {src:'Crittr:hurt', w:3}, {src:'Crittr:lose', w:1}, {src:'Breathr:hurt', w:1}, {src:'Squishr:hurt', w:1}, {src:'Glitchr:hurt', w:1},
            {mix:['Bfxr:hurt','Breathr:hurt'], balance:[0.4,0.55], align:0, w:1},
            {mix:['Bfxr:hurt','Crittr:hurt'], balance:[0.35,0.5], align:0, w:1}],
        explode: [
            {src:'Bfxr:explode', w:4}, {src:'Boomr:explode', w:3}, {src:'Transfxr:explode', w:3}, {src:'Boomr:generate_grenade', w:1}, {src:'Boomr:generate_barrel', w:1},
            {mix:['Boomr:explode','Fractr:break'], balance:[0.3,0.45], align:1, w:1},
            {mix:['Boomr:explode','Breathr:roar'], balance:[0.25,0.4], align:0, w:1},
            {mix:['Bfxr:explode','Boomr:explode'], balance:[0.4,0.6], align:0, w:1}],
        coin: [
            {src:'Bfxr:coin', w:5}, {src:'Bfxr:generate_reference_coin', w:2}, {src:'Transfxr:coin', w:4}, {src:'Jinglr:coin', w:2}, {src:'Pluckr:coin', w:1}, {src:'Bouncr:coin', w:1}, {src:'Clonkr:coin', w:1},
            {mix:['Bfxr:coin','Bouncr:coin'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Jinglr:coin','Clonkr:coin'], balance:[0.4,0.55], align:0, w:1}],
        powerup: [
            {src:'Bfxr:powerup', w:4}, {src:'Transfxr:powerup', w:4}, {src:'Jinglr:powerup', w:2}, {src:'Choirr:powerup', w:1},
            {mix:['Bfxr:powerup','Choirr:powerup'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Bfxr:powerup','Zappr:cast'], balance:[0.3,0.45], align:1, w:1}],
        unlock: [
            {src:'Jinglr:unlock', w:3}, {src:'Transfxr:unlock', w:3}, {src:'Machinr:unlock', w:3}, {src:'Clonkr:blip', w:1}, {src:'Pluckr:unlock', w:1}, {src:'Signlr:unlock', w:1}, {src:'Rustlr:unlock', w:1},
            {mix:['Machinr:unlock','Jinglr:coin'], balance:[0.45,0.6], align:2, w:2},
            {mix:['Jinglr:unlock','Clonkr:coin'], balance:[0.35,0.5], align:0, w:1}],
        win: [
            {src:'Jinglr:win', w:4}, {src:'Jinglr:generate_puzzle_solved', w:1}, {src:'Jinglr:generate_checkpoint', w:1}, {src:'Choirr:win', w:2}, {src:'Transfxr:win', w:2},
            {mix:['Jinglr:win','Swarmr:cast'], balance:[0.25,0.4], align:0, w:1}],
        lose: [
            {src:'Jinglr:lose', w:4}, {src:'Transfxr:lose', w:3}, {src:'Choirr:lose', w:1}, {src:'Riftr:lose', w:1}, {src:'Glitchr:lose', w:1}, {src:'Breathr:lose', w:1}, {src:'Crittr:lose', w:1},
            {mix:['Jinglr:lose','Breathr:lose'], balance:[0.3,0.45], align:0, w:1},
            {mix:['Bfxr:hurt','Jinglr:lose'], balance:[0.4,0.55], align:2, w:2}],
        break: [
            {src:'Fractr:break', w:5}, {src:'Transfxr:break', w:3}, {src:'Clonkr:break', w:2}, {src:'Rustlr:generate_wrapper', w:1},
            {mix:['Fractr:break','Boomr:hit'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Clonkr:break','Fractr:break'], balance:[0.35,0.5], align:0, w:1}],
        door: [
            {src:'Machinr:door', w:3}, {src:'Transfxr:door', w:4}, {src:'Clonkr:door', w:2}, {src:'Whooshr:door', w:1}, {src:'Rumblr:generate_stone_door', w:1}, {src:'Machinr:generate_heavy_door', w:1},
            {mix:['Whooshr:door','Clonkr:hit'], balance:[0.4,0.55], align:2, w:2},
            {mix:['Transfxr:door','Clonkr:hit'], balance:[0.35,0.5], align:2, w:1}],
        blip: [
            {src:'Bfxr:blip', w:5}, {src:'Transfxr:blip', w:4}, {src:'Tappr:generate_select', w:1}, {src:'Tappr:generate_focus', w:1}, {src:'Signlr:blip', w:1}, {src:'Pluckr:blip', w:1},
            {src:'Glitchr:blip', w:1}, {src:'Clonkr:blip', w:1}, {src:'Squishr:blip', w:1}],
        confirm: [
            {src:'Jinglr:confirm', w:4}, {src:'Transfxr:confirm', w:4}, {src:'Machinr:confirm', w:1}, {src:'Birdr:confirm', w:1}, {src:'Crittr:confirm', w:1}, {src:'Pluckr:confirm', w:1},
            {src:'Signlr:confirm', w:1}, {src:'Rustlr:confirm', w:1}, {src:'Tappr:generate_panel_open', w:1}, {src:'Notifr:generate_objective_done', w:1}, {src:'Notifr:generate_message', w:1},
            {mix:['Tappr:generate_select','Jinglr:confirm'], balance:[0.45,0.6], align:0, w:1}],
        alert: [
            {src:'Jinglr:alert', w:2}, {src:'Transfxr:alert', w:5}, {src:'Jinglr:generate_denied', w:3}, {src:'Signlr:alert', w:2}, {src:'Zappr:alert', w:1}, {src:'Birdr:alert', w:1}, {src:'Glitchr:alert', w:1},
            {mix:['Signlr:alert','Zappr:alert'], balance:[0.3,0.45], align:0, w:1}],
        cast: [
            {src:'Zappr:cast', w:3}, {src:'Transfxr:cast', w:4}, {src:'Choirr:cast', w:1}, {src:'Riftr:cast', w:1}, {src:'Fractr:cast', w:1}, {src:'Swarmr:cast', w:1}, {src:'Jinglr:cast', w:1},
            {mix:['Zappr:cast','Choirr:cast'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Riftr:cast','Fractr:cast'], balance:[0.35,0.5], align:1, w:1}],
        warp: [
            {src:'Riftr:warp', w:4}, {src:'Transfxr:warp', w:4}, {src:'Signlr:warp', w:1}, {src:'Glitchr:warp', w:1}, {src:'Riftr:generate_teleport_arrive', w:1},
            {mix:['Riftr:warp','Glitchr:warp'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Riftr:warp','Whooshr:dash'], balance:[0.45,0.6], align:0, w:1}],
        roar: [
            {src:'Crittr:roar', w:5}, {src:'Transfxr:roar', w:4}, {src:'Breathr:roar', w:1}, {src:'Crittr:generate_cave_beast', w:1}, {src:'Crittr:generate_angry_blob', w:1},
            {src:'Birdr:generate_crow', w:1},
            {mix:['Crittr:roar','Boomr:land'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Transfxr:roar','Breathr:roar'], balance:[0.4,0.55], align:0, w:1}],
        whirr: [
            {src:'Machinr:whirr', w:4}, {src:'Transfxr:whirr', w:4}, {src:'Swarmr:whirr', w:1}, {src:'Zappr:whirr', w:1}, {src:'Zappr:generate_tesla_coil', w:1},
            {src:'Pulser:generate_android_core', w:1}, {src:'Pulser:generate_energy_core', w:1}, {src:'Rollr:generate_minecart', w:1}, {src:'Rollr:generate_metal_roller', w:1},
            {src:'Swarmr:generate_drone_patrol', w:1}, {src:'Signlr:generate_broken_radio', w:1}, {src:'Rumblr:generate_engine_room', w:1},
            {mix:['Machinr:whirr','Zappr:whirr'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Rollr:generate_minecart','Machinr:whirr'], balance:[0.4,0.55], align:0, w:1}],
        heal: [
            {src:'Choirr:heal', w:2}, {src:'Transfxr:heal', w:4}, {src:'Pluckr:heal', w:2}, {src:'Jinglr:heal', w:2}, {src:'Squishr:heal', w:1}, {src:'Swarmr:heal', w:1},
            {mix:['Pluckr:heal','Swarmr:heal'], balance:[0.35,0.5], align:0, w:1},
            {mix:['Jinglr:heal','Squishr:heal'], balance:[0.3,0.45], align:0, w:1}]
    };
    recipes = GAME_VERBS.map(verb => ({name:verb.name, id:verb.id, verb:verb.id, tip:verb.tip, values:{}}));
    constructor() { super(); this.initialize_presets(); this.last_entries = {}; }
    create_editor(tab, parent) { return new BoardEditor(tab, parent); }

    static entries(verb) { return this.catalogue[verb] || []; }
    static entry_references(entry) { return entry.mix ? entry.mix : [entry.src]; }
    // Every reference in the catalogue, for validation.
    static references() {
        return Object.values(this.catalogue).flatMap(entries => entries.flatMap(entry => this.entry_references(entry)));
    }
    // Weighted draw that avoids the previous entry when there is a choice.
    pick_entry(verb) {
        const entries = Soundboard.entries(verb);
        if (!entries.length) return null;
        const previous = this.last_entries[verb];
        const candidates = entries.length > 1 ? entries.filter(entry => entry !== previous) : entries;
        const total = candidates.reduce((sum, entry) => sum + (entry.w || 1), 0);
        let roll = Math.random() * total;
        for (const entry of candidates) { roll -= entry.w || 1; if (roll < 0) return entry; }
        return candidates[candidates.length - 1];
    }
    apply_entry(entry) {
        const sources = Soundboard.entry_references(entry).map(reference => {
            const source = Soundboard.verb_source(reference);
            if (!source) throw new Error('Unknown Soundboard ingredient: ' + reference);
            return source;
        });
        this.set_param('sources', sources);
        const balance = Array.isArray(entry.balance) ? entry.balance[0] + Math.random() * (entry.balance[1] - entry.balance[0]) : Number.isFinite(entry.balance) ? entry.balance : 0.5;
        this.set_param('balance', balance, true);
        this.set_param('align', entry.align || 0, true);
        this.set_param('offset', Number.isFinite(entry.offset) ? entry.offset : 0, true);
    }
    after_recipe(recipe) {
        if (this.locked_param('sources')) return;
        const entry = this.pick_entry(recipe.id);
        if (!entry) return;
        this.last_entries[recipe.id] = entry;
        this.current_verb = recipe.id;
        this.apply_entry(entry);
    }
    // The verb of the last board press, or the one implied by saved sources.
    verb() { return this.current_verb || null; }
    generate_verb(verb) { if (game_verb(verb)) this.generate_recipe(verb); }
    randomize_params() { this.generate_recipe(GAME_VERBS[Math.floor(Math.random() * GAME_VERBS.length)].id); }
    // A human-readable account of the current ingredients.
    describe() {
        const sources = this.get_sources().filter(Boolean);
        const names = sources.map(source => synth_display_name(source.synth) + ' · ' + source.name);
        if (!names.length) return 'Press a verb.';
        if (names.length === 1) return names[0];
        const align = ['start-aligned', 'peak-aligned', 'tail-aligned'][Math.round(this.params.align) || 0];
        return names.join(' × ') + ' (' + align + ')';
    }
}
