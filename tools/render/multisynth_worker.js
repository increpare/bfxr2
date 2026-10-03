#!/usr/bin/env node
'use strict';
const readline = require('node:readline');
const {createMultisynthContext} = require('./multisynth_context');
const api = createMultisynthContext();
const lines = readline.createInterface({input:process.stdin, crlfDelay:Infinity});
lines.on('line', line => {
    if (!line.trim()) return;
    let response;
    try {
        const request = JSON.parse(line);
        if (!request || typeof request !== 'object') throw new Error('Request must be an object');
        switch (request.op) {
            case 'inventory': response = api.inventory(); break;
            case 'sample': response = {params:api.sample(request.synth,request.preset,request.seed)}; break;
            case 'render': {
                const {params,pcm} = api.render(request.synth,request.params,request.seed);
                const buffer = Buffer.allocUnsafe(pcm.length * 4);
                for (let i = 0; i < pcm.length; i++) buffer.writeFloatLE(pcm[i], i * 4);
                response = {sampleRate:44100,params,audio:buffer.toString('base64')};
                break;
            }
            default: throw new Error('Unknown operation: ' + request.op);
        }
        response = {ok:true,...response};
    } catch (error) { response = {ok:false,error:error.message}; }
    process.stdout.write(JSON.stringify(response) + '\n');
});
