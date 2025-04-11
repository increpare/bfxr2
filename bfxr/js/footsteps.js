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
    envelope_signal = pd_mul(envelope_signal,pd_c(step_vol));


    var signal = pd_noise();
    var v_200 = pd_c(200);
    var v_1 = pd_c(1);
    var signal = pd_vcf(signal, v_200, v_1);

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

    signal = pd_clip(signal,-1,1);
    signal = pd_hip(signal,pd_c(300));

    signal = pd_mul(signal,envelope_signal);

    signal = pd_clip(signal, -1.0, 1.0);
    signal = pd_mul(signal, pd_c(0.5));

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

