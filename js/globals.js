Math.clamp = function(value, min, max){
    return Math.max(min, Math.min(value, max));
}

const SYNTH_DISPLAY_NAMES = {
    Transfxr:'Transfxr', Clonkr:'Tangs', Machinr:'Motors',
    Jinglr:'Jingles', Squishr:'Squishy', Mixr:'Mixfxr',
    Crittr:'Beasts', Birdr:'Bird', Signlr:'Signal',
    Fractr:'Cracker', Riftr:'Sonar', Swarmr:'Swarms',
    Rustlr:'Rustler', Boomr:'Boomer', Zappr:'Zapper',
    Whooshr:'Whoosh', Bouncr:'Bonks', Breathr:'Breath',
    Choirr:'Choir', Pluckr:'Plucked', Glitchr:'Glitches'
};

function synth_display_name(name) {
    return SYNTH_DISPLAY_NAMES[name] || name;
}

// shallow copy
function copy_obj(obj){
    return Object.assign({}, obj);
}

function step(n){
    return function(x){
        if (x<=0 || x>=1) return 0;
        return ((x*x*x)*n-x*n)*(1-x)*(-1.5);
    }
}

function resize_fn(fn,a1,a2,b1,b2){
    return function(y){
        return fn( (y-b1)/(b2-b1) * (a2-a1) + a1 );
    }      
}

function add_fns( ...fns ){
    return function(x){                
        return fns.reduce((acc,fn) => acc + fn(x), 0);
    }
}

function isVisible (ele, container) {
    const eleTop = ele.offsetTop;
    const eleBottom = eleTop + ele.clientHeight;

    const containerTop = container.scrollTop;
    const containerBottom = containerTop + container.clientHeight;

    // The element is fully visible in the container
    return (
        (eleTop >= containerTop && eleBottom <= containerBottom) ||
        // Some part of the element is visible in the container
        (eleTop < containerTop && containerTop < eleBottom) ||
        (eleTop < containerBottom && containerBottom < eleBottom)
    );
};

function setVisible (ele, container) {
    if (isVisible(ele, container)){
        return;
    }
    //if above
    if (ele.offsetTop < container.scrollTop){
        container.scrollTop = ele.offsetTop;
    }
    //if below
    else if (ele.offsetTop + ele.offsetHeight > container.scrollTop + container.offsetHeight){
        container.scrollTop = ele.offsetTop - container.offsetHeight + ele.offsetHeight;
    }
}

function lerp(a, b, t){
    return a + t * (b - a);
}

// The shared vocabulary of game verbs. Engine verb presets, Mixfxr verb recipes and the
// Soundboard all refer to these ids. Duration is the expected active length in seconds.
const GAME_VERBS = [
    {id:'jump', name:'Jump', row:'Move', tip:'Leave the ground: a quick upward push.', duration:[0.06,0.6]},
    {id:'land', name:'Land', row:'Move', tip:'Arrive back on the ground with some weight.', duration:[0.04,0.9]},
    {id:'step', name:'Step', row:'Move', tip:'One footstep on some surface.', duration:[0.04,0.75]},
    {id:'dash', name:'Dash', row:'Move', tip:'A burst of speed or a dodge.', duration:[0.12,1]},
    {id:'splash', name:'Splash', row:'Move', tip:'Hit or move through liquid.', duration:[0.12,1.3]},
    {id:'shoot', name:'Shoot', row:'Fight', tip:'Fire a projectile, beam or bolt.', duration:[0.06,0.9]},
    {id:'swing', name:'Swing', row:'Fight', tip:'A melee attack moving through the air.', duration:[0.12,1]},
    {id:'hit', name:'Hit', row:'Fight', tip:'Something gets struck.', duration:[0.02,0.7]},
    {id:'hurt', name:'Hurt', row:'Fight', tip:'The player or a creature takes damage.', duration:[0.08,0.9]},
    {id:'explode', name:'Explode', row:'Fight', tip:'A blast with debris.', duration:[0.08,3.5]},
    {id:'coin', name:'Coin', row:'Reward', tip:'Pick up a small shiny thing.', duration:[0.06,0.9]},
    {id:'powerup', name:'Powerup', row:'Reward', tip:'Gain a power: bright and rising.', duration:[0.08,2]},
    {id:'unlock', name:'Unlock', row:'Reward', tip:'A secret, a door or a chest opens up.', duration:[0.15,2.8]},
    {id:'win', name:'Win', row:'Reward', tip:'Success: a level cleared or a goal met.', duration:[0.6,3.8]},
    {id:'lose', name:'Lose', row:'Reward', tip:'Failure, defeat or death.', duration:[0.4,3.5]},
    {id:'break', name:'Break', row:'World', tip:'An object shatters, snaps or crumbles.', duration:[0.1,2]},
    {id:'door', name:'Door', row:'World', tip:'A door, gate or hatch moves and latches.', duration:[0.25,2.5]},
    {id:'blip', name:'Blip', row:'World', tip:'A tiny cursor tick or text beep.', duration:[0.01,0.3]},
    {id:'confirm', name:'Confirm', row:'World', tip:'Yes: a menu choice accepted.', duration:[0.06,1]},
    {id:'alert', name:'Alert', row:'World', tip:'Attention, warning or a refused action.', duration:[0.12,1.8]},
    {id:'cast', name:'Cast', row:'Fantasy', tip:'Magic leaves the caster.', duration:[0.25,2.2]},
    {id:'warp', name:'Warp', row:'Fantasy', tip:'Teleport, portal or phase shift.', duration:[0.25,2.8]},
    {id:'roar', name:'Roar', row:'Fantasy', tip:'A big creature announces itself.', duration:[0.3,2.8]},
    {id:'whirr', name:'Whirr', row:'Fantasy', tip:'A small machine runs for a moment.', duration:[0.3,3]},
    {id:'heal', name:'Heal', row:'Fantasy', tip:'Restoration: soft, warm and rising.', duration:[0.3,2.8]}
];
function game_verb(id) { return GAME_VERBS.find(verb => verb.id === id) || null; }
