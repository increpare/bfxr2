checkAudioContextExists();

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

function gen_base_snow(envelope_signal){
    var signal = pd_noise();
    var v_200 = pd_c(200);
    var v_1 = pd_c(1);
    signal = pd_vcf(signal, v_200, v_1);

    var base_noise = pd_noise();
    var alt_noise = pd_noise();

    signal = base_noise;
    signal = pd_div(
        pd_lop(signal,pd_c(110)),
        pd_lop(signal,pd_c(900)));

    var side_div = pd_div(
        pd_lop(alt_noise,pd_c(50)),
        pd_lop(alt_noise,pd_c(70)));

    signal = pd_mul(signal,side_div)
    
    var s1_lop = pd_lop(alt_noise,pd_c(10));
    var s2_mul = pd_mul(s1_lop,pd_c(17));
    var s3_sqr = pd_mul(s2_mul,s2_mul);
    var s4_add = pd_add(s3_sqr,pd_c(0.5));

    signal = pd_mul(signal,s4_add);

    signal = pd_clip(signal,pd_c(-1),pd_c(1));
    signal = pd_hip(signal,pd_c(300));

    var to_mix = pd_add(pd_mul(envelope_signal,pd_c(9000)),pd_c(700));    
    signal = pd_vcf(signal,to_mix,pd_c(0.5))
    signal = pd_mul(signal,envelope_signal);
    signal = pd_mul(signal,pd_c(0.2));
    return signal;
}

function gen_base_dirt(envelope_signal){
    //right column
    var source_noise = pd_noise();
    var filtered_noise = pd_lop(source_noise,pd_c(80));
    filtered_noise = pd_mul(filtered_noise,pd_c(70));
    var signal_plus_0_3 = pd_add(envelope_signal,pd_c(0.3));
    var mix = pd_mul(filtered_noise,signal_plus_0_3);
    mix = pd_mul(mix,pd_c(70));
    mix = pd_add(mix,pd_c(70));
    var osc_r = pd_osc(mix);
    var hip_r = pd_hip(osc_r,pd_c(200));
    var clipper_r = pd_clip(hip_r,pd_c(-1),pd_c(1));
    clipper_r = pd_mul(clipper_r,pd_c(0.04));

    //left column
    var quad_envelope = pd_mul(envelope_signal,envelope_signal);
    quad_envelope = pd_mul(quad_envelope,quad_envelope);
    var ll = pd_mul(quad_envelope,pd_c(500));
    ll = pd_add(ll,pd_c(40));
    var osc_l = pd_osc(ll);

    var mul_l = pd_mul(osc_l,quad_envelope);
    var osc_l_2 = pd_mul(mul_l,pd_c(0.5));

    var sum_l = pd_add(osc_l_2,clipper_r);
    return sum_l;
}

//cf. with osc.pd
function pd_test_osc(envelope_signal){
    var signal = pd_osc(pd_c(1));
    signal = pd_mul(signal,pd_c(200));
    signal = pd_osc(signal);
    signal = pd_clip(signal,pd_c(-1),pd_c(1));
    signal = pd_mul(signal,pd_c(0.5));
    return signal;
}
function pd_test_slotsum(envelope_signal){
    var osc1 = pd_osc(pd_c(200));
    var osc2 = pd_osc(pd_c(400));
    var signal = pd_mul(pd_polyadd(osc1,osc2),pd_c(0.5));
    signal = pd_clip(signal,pd_c(-1),pd_c(1));
    signal = pd_mul(signal,pd_c(0.5));
    return signal;
}

function gen_base_grass(envelope_signal){
    var source_noise = pd_noise();
    var signal=source_noise;

    var lop_main = pd_lop(signal,pd_c(300));
    var lop_side = pd_lop(signal,pd_c(2000));
    signal = pd_mul(lop_main,lop_side);
    signal = pd_hip(signal,pd_c(2500));
    signal = pd_mul(signal,signal);
    signal = pd_mul(signal,signal);
    signal = pd_mul(signal,pd_c(1e-5));
    signal = pd_clip(signal,pd_c(-0.9),pd_c(0.9));
    
    var side_noise = pd_lop(source_noise,pd_c(16));
    side_noise = pd_mul(side_noise,pd_c(23800));
    side_noise = pd_add(side_noise,pd_c(3400));
    side_noise = pd_clip(side_noise, pd_c(2000),pd_c(10000));

    signal = pd_vcf(signal,side_noise,pd_c(1.0));
    signal = pd_hip(signal,pd_c(900));
    signal = pd_mul(signal,0.3);
    signal = pd_mul(signal,envelope_signal);

    var left_path = envelope_signal;
    left_path = pd_mul(left_path,left_path);
    left_path = pd_mul(left_path,left_path);
    var left_branch = left_path;
    left_branch = pd_mul(left_branch,pd_c(600));
    left_branch = pd_add(left_branch,30);
    left_branch = pd_osc(left_branch);
    left_branch = pd_clip(left_branch,pd_c(0),pd_c(0.5));
    left_path = pd_mul(left_branch,left_path);
    left_path = pd_mul(left_path,pd_c(0.8));
    signal = pd_add(signal,left_path);
    return signal;
}


function generate_terrain_texture(envelope_signal){
    /*
    [S]
    */
    switch (step_terrain){
        case 0://snow
            // return pd_test_slotsum(envelope_signal);
            // return gen_base_dirt(envelope_signal);
            // return gen_base_snow(envelope_signal);
            return puredata_functions["wood"](envelope_signal);
        case 1://grass
            return gen_base_grass(envelope_signal);
        default:
            return pd_mul(pd_noise(),envelope_signal);            
    }

}
function generateSound(step_heel,step_roll,step_ball,step_speed,step_vol){
    
    //speed is between 0 and 1, this corresponds to a step-length between 0.8 and 0.1 
    var step_length = 0.1+0.7*(1-step_speed)
    
    //constant signal 0 
    pd_set_stream_length_seconds(step_length);

    var heel_envelope = resize_fn(step(step_heel),0,1,0,0.3333);
    var roll_envelope = resize_fn(step(step_roll),0,1,0.125,0.875);
    var ball_envelope = resize_fn(step(step_ball),0,1,0.6667,1);
    var step_envelope_0_1 = add_fns(heel_envelope,roll_envelope,ball_envelope);
    var step_envelope_resized = resize_fn(step_envelope_0_1,0,1,0,step_length);

    var envelope_signal = pd_fn(step_envelope_resized);

    var signal = generate_terrain_texture(envelope_signal);

    signal = pd_mul(signal,pd_c(step_vol));
    signal = pd_clip(signal, pd_c(-1.0), pd_c(1.0));
    // signal = pd_mul(signal, pd_c(0.5));

    var sound = RealizedSound.from_buffer(signal);
    
    console.log("updating canvas");
    clearCanvas();
    drawWaveform([step_heel,step_roll,step_ball,step_length,step_vol],sound);
    drawFootstep(step_heel,step_roll,step_ball,step_length,step_envelope_resized);

    return sound;
}

function playFootsteps(step_heel,step_roll,step_ball,step_speed,step_vol) {

    //step_
    checkAudioContextExists();

    var sound = generateSound(step_heel,step_roll,step_ball,step_speed,step_vol);
    sound.play();
    return sound;

}

var imageCache = {};
function cacheImage(params,width,sound){
    var str_rep = JSON.stringify(params);
   
    if (str_rep in imageCache) {
        return imageCache[str_rep];
    }

    var result=[];
    
    var buffer=sound.getBuffer();

    var curbar=0;
    var curmax=buffer[0];
    var curmin=buffer[0];
    var len=buffer.length;
    for (var i=0;i<len;i++){
        var val = buffer[i];
        if (i/len>curbar/width){
            result.push(curmax);
            result.push(curmin);
            curbar++;
            curmin=val;
            curmax=val;
        } else {
            if (val<curmin) {
                curmin=val;
            }
            if (val>curmax) {
                curmax=val;
            }
        }
    }
    result.push(curmax);
    result.push(curmin);

    imageCache[str_rep]=result;

    return result;
}

function clearCanvas(){
    const canvasEle = document.getElementById('logo-canvas');
    const context2d = canvasEle.getContext('2d');
    context2d.clearRect(0, 0, canvasEle.width, canvasEle.height);
}

function drawWaveform(params,sound){
    const canvasEle = document.getElementById('logo-canvas');
    const context2d = canvasEle.getContext('2d');

    var w = canvasEle.width;
    var h = canvasEle.height;
    var margin = 4;
    var bmargin = 4;
    

    h = h - margin - bmargin;
    w = w - 2 * margin;

    
    var t = margin;
    var b = t + h;
    var l = margin;
    var r = l + w;
    
    var c = t + h/2;

    let graphwidth = canvasEle.width;
    var silhouette = cacheImage(params,graphwidth,sound);
    
    context2d.beginPath();
    context2d.lineWidth = '1'; // width of the line
    context2d.strokeStyle = '#663931'; // color of the line

    for (var i=0;i<graphwidth;i++){
        var x = l+i;
        var u = c+silhouette[2*i+0]*1*h;
        var d = c+silhouette[2*i+1]*1*h;

        context2d.moveTo(x, u); // begins a new sub-path based on the given x and y values.
        context2d.lineTo(x, d); // used to create a pointer based on x and y  
    }
  
    context2d.stroke();

}

function drawFootstep(step_heel,step_roll,step_ball,step_length,step_envelope_resized){
    const canvasEle = document.getElementById('logo-canvas');
    const context2d = canvasEle.getContext('2d');

    var w = canvasEle.width;
    var h = canvasEle.height;
    var margin = 4;
    var bmargin = 40;

    h = h - margin - bmargin;
    w = w - 2 * margin;

    var volume = step_vol;

    var t = margin;
    var b = t + h;
    var l = margin;
    var r = l + w;

    
    context2d.beginPath();
    context2d.lineWidth = '5'; // width of the line
    context2d.lineCap = "round";
    context2d.lineJoin = "round";
    context2d.strokeStyle = '#c8905780'; //'#c89057'; // color of the line

    
    var last_x = 0;
    var last_y = 0;
    let graphwidth = canvasEle.width;
    for (var i=0;i<graphwidth;i++){
        //we're going to draw the envelope
        var t = (i/graphwidth)*step_length;
        
        var p = step_envelope_resized(t)*step_vol;

        var x = i;
        var y = b - 2*h*p;
        
        if (i==0){
            last_y = y;
        }

        context2d.moveTo(last_x, last_y);
        context2d.lineTo(x, y);
        last_x = x;
        last_y = y;
       
    }

    context2d.stroke();
}

var step_vol=1.0;
var step_heel=0.5;
var step_roll=0.5;
var step_ball=0.5;
var step_speed=0.5;
var step_terrain=0;

if (typeof exports != 'undefined') {
    // For node.js
    var RIFFWAVE = require('./riffwave').RIFFWAVE;
    exports.Params = Params;
    exports.generate = generate;
}

function doPlay(){
    var sound = playFootsteps(step_heel,step_roll,step_ball,step_speed,step_vol);  
    var link = document.getElementById("save_wav");

    link.href = sound.getDataUri();
    link.download = "footstep.wav";
}

var button_play = document.getElementById("button_play");
button_play.addEventListener("click", function(event) {
    doPlay();  
});

