#!/usr/bin/env python3
"""Author the semantic palette from the user's listening notes and survey states."""
import json
from pathlib import Path

def row(name,start,end,curve):
    return {name+'.start':start,name+'.end':end,name+'.curve':curve}

def profiles():
    base={'waveTo':-1}
    def profile(id,name,source,tip,limits,intervals=None,preserve=False):
        return dict(id=id,name=name,source_group=source,tip=tip,limits={**base,**limits},
            intervals=intervals or {},preserve=preserve,variation={'pitch':.035,'tone':.06,'noise':.025,'vibrato':.05,'level':.06})
    clean={'echo':0,'resonance':[.08,.3]}
    return [
        profile('bright_whistles','Bright Whistles','Bright Whistles','Clear, bright electronic whistles with a clean ringing voice.',{},preserve=True),
        profile('grainy_taps','Grainy Taps','Grainy Taps','Dry, low gritty taps. A single quick attack, with no long tail.',
            {'waveType':2,'duration':[.065,.17],'attack':[.001,.006],'release':[.045,.14],'echo':0,'resonance':[.12,.4],
             **row('pitch',[.34,.48],[.27,.43],'Ease Out'),**row('tone',[.32,.52],[.28,.46],'Ease Out'),
             **row('noise',[.72,.92],[.65,.85],'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.7,.95],[.08,.25],'Ease Out')}),
        profile('rocket_zips','Rocket Zips','Rocket Zips','A short hollow arcade whistle that rockets upwards and cuts off.',
            {'waveType':3,'duration':[.22,.4],'attack':[.001,.008],'release':[.1,.25],**clean,
             **row('pitch',[.14,.27],[.64,.8],'Ease Out'),**row('tone',[.65,.85],[.78,.95],'Linear'),
             **row('noise',[0,.05],[0,.05],'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.65,.85],[.3,.6],'Linear')}),
        profile('wavering_calls','Wavering Calls','Wavering Calls','A rounded voice with an audible, steady quiver throughout the call.',
            {'waveType':1,'duration':[.7,1.2],'attack':[.025,.08],'release':[.18,.4],**clean,
             **row('pitch',[.38,.55],[.31,.62],'Smooth'),**row('tone',[.6,.78],[.58,.75],'Smooth'),
             **row('noise',[0,.06],[0,.06],'Linear'),**row('vibrato',[.72,.9],[.72,.9],'Linear'),
             **row('level',[.6,.8],[.4,.65],'Smooth')},{'pitch':[-.07,.07]}),
        profile('fuzzy_chirps','Fuzzy Chirps','Fuzzy Chirps','Tiny bright buzzes with a pitched chirp inside a fuzzy edge.',
            {'waveType':2,'duration':[.09,.25],'attack':[.001,.006],'release':[.055,.16],'echo':0,'resonance':[.12,.35],
             **row('pitch',[.57,.7],[.69,.8],'Pulse'),**row('tone',[.68,.88],[.6,.8],'Ease Out'),
             **row('noise',[.2,.38],[.2,.38],'Linear'),**row('vibrato',[0,.12],[0,.12],'Linear'),
             **row('level',[.6,.8],[.15,.35],'Ease Out')}),
        profile('bass_plucks','Bass Plucks','Bass Plucks','Low rounded notes with a quick onset and a soft tail.',{},preserve=True),
        profile('soft_pips','Soft Pips','Soft Pips','Gentle, clean sine pips with a cushioned onset and almost no pitch motion.',
            {'waveType':0,'duration':[.1,.19],'attack':[.014,.028],'release':[.06,.14],'echo':0,'resonance':[0,.1],
             **row('pitch',[.42,.55],[.395,.565],'Ease Out'),**row('tone',[.48,.62],[.43,.58],'Smooth'),
             **row('noise',0,0,'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.38,.55],[.18,.35],'Smooth')},
             {'pitch':[-.025,.015]}),
        profile('sand_sprays','Sand Sprays','Sand Sprays','A short bright powdery spray: all grain, with no pitched note.',
            {'waveType':0,'duration':[.14,.42],'attack':[.001,.01],'release':[.08,.2],'echo':0,'resonance':[0,.15],
             **row('pitch',[.3,.45],[.3,.45],'Linear'),**row('tone',[.64,.8],[.63,.79],'Linear'),
             **row('noise',1,1,'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.65,.9],[.2,.45],'Ease Out')}),
        profile('air_currents','Air Currents','Air Currents','A longer, dark breath of air that eases in and out smoothly.',
            {'waveType':0,'duration':[.9,1.65],'attack':[.2,.45],'release':[.35,.65],'echo':0,'resonance':[.05,.22],
             **row('pitch',[.25,.4],[.25,.4],'Linear'),**row('tone',[.32,.47],[.31,.46],'Smooth'),
             **row('noise',1,1,'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.55,.8],[.4,.65],'Smooth')}),
        profile('submarine_calls','Mournful Calls','Submarine Calls','Low, woozy electronic calls with a plaintive, fading voice.',{},preserve=True),
        profile('arcade_zaps','Arcade Zaps','Descending Sweeps','A sharp sawtooth zap with a quick diving pitch and a bright sting.',
            {'waveType':2,'duration':[.12,.27],'attack':[0,.003],'release':[.075,.18],'echo':0,'resonance':[.2,.45],
             **row('pitch',[.67,.84],[.18,.3],'Ease Out'),**row('tone',[.78,.95],[.25,.45],'Ease Out'),
             **row('noise',[0,.06],[0,.06],'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.75,.95],[.08,.25],'Ease Out')}),
        profile('bubble_pops','Bubble Pops','Rising Bloops','Round little water-note pops: a sine voice that curls up and back.',
            {'waveType':0,'duration':[.12,.28],'attack':[.001,.004],'release':[.065,.2],'echo':0,'resonance':[.15,.4],
             **row('pitch',[.23,.38],[.43,.65],'Pulse'),**row('tone',[.55,.7],[.5,.65],'Smooth'),
             **row('noise',0,0,'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.7,.9],[.05,.2],'Ease Out')},
             {'pitch':[.15,.3]}),
        profile('rubber_clicks','Rubber Clicks','Rubber Clicks','Short rubbery ticks and cushioned clicks, kept close to the original voice.',
            {'duration':[.065,.25],'echo':0},preserve=True),
        profile('bubble_swells','Bubble Swells','Reverse Bloops','A rounded sine bloop that swells to a small peak, then stops.',
            {'waveType':0,'duration':[.28,.5],'attack':[.19,.36],'release':[.035,.065],'echo':0,'resonance':[.08,.25],
             **row('pitch',[.37,.5],[.4,.55],'Smooth'),**row('tone',[.47,.62],[.55,.7],'Smooth'),
             **row('noise',0,0,'Linear'),**row('vibrato',0,0,'Linear'),**row('level',[.35,.55],[.65,.85],'Ease In')},
             {'pitch':[0,.055]}),
        profile('static_flecks','Radio Spits','Static Flecks','Brief fragments of filtered radio grit, dry and rough around the edges.',
            {'duration':[.065,.32],'echo':0},preserve=True),
    ]

if __name__=='__main__':
    path=Path(__file__).with_name('family_profiles.json')
    path.write_text(json.dumps({'revision':2,'basis':'User listening feedback on the first six catalogue exemplars, 2026-10-02','families':profiles()},indent=2)+'\n')
    print('Wrote',path)
