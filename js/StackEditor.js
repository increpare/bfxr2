class StackEditor {
    constructor(tab, parent) {
        this.tab = tab;
        this.root = document.createElement('section');
        this.root.className = 'stack-editor';
        const heading = document.createElement('h3');
        heading.textContent = 'Build a little event';
        this.root.appendChild(heading);
        const note = document.createElement('p');
        note.textContent = 'Layer copies of sounds from any other tab. Move them in time, change their level, or shift their pitch.';
        this.root.appendChild(note);
        this.timeline = document.createElement('div');
        this.timeline.className = 'stack-timeline';
        this.timeline.setAttribute('aria-label','Layer timeline');
        this.root.appendChild(this.timeline);
        this.rows = document.createElement('div');
        this.root.appendChild(this.rows);
        const actions = document.createElement('div');
        actions.className = 'stack-actions';
        this.source = document.createElement('select');
        this.source.setAttribute('aria-label','Sound to add');
        actions.appendChild(this.source);
        this.add = document.createElement('button');
        this.add.textContent = 'Add layer';
        this.add.addEventListener('click',()=>{
            const [name,index] = this.source.value.split(':');
            const sourceTab = tabs.find(t=>t.name===name);
            if (!sourceTab || !sourceTab.files[+index]) return;
            const source = Stackr.source(name);
            const file = sourceTab.files[+index];
            source.apply_params(JSON.parse(file[1]));
            tab.synth.add_source(source,file[0]);
            tab.parameter_changed();
            this.update();
        });
        actions.appendChild(this.add);
        this.lock = document.createElement('button');
        this.lock.addEventListener('click',()=>{
            tab.synth.set_locked_param('layers',!tab.synth.locked_param('layers'));
            SaveLoad.save_all_collections();this.update();
        });
        actions.appendChild(this.lock);
        this.root.appendChild(actions);
        const limits = document.createElement('small');
        limits.textContent = 'Up to 6 layers · 12 seconds total · copies travel with saved files';
        this.root.appendChild(limits);
        parent.appendChild(this.root);
        this.update();
    }
    update() {
        const synth = this.tab.synth;
        const layers = synth.get_layers();
        this.rows.replaceChildren();
        this.timeline.replaceChildren();
        const extent = Math.min(12,Math.max(1,...layers.map((layer,i)=>layer.start * synth.params.spacing + (synth.layer_durations?.[i] || 1))));
        layers.forEach((layer,index)=>{
            const row = document.createElement('div');row.className='stack-layer';
            const title=document.createElement('strong');title.textContent=(index+1)+'. '+layer.name;
            const kind=document.createElement('small');kind.textContent=layer.synth;title.appendChild(kind);row.appendChild(title);
            const change = (key,value) => {
                const updated=synth.get_layers();updated[index][key]=value;synth.set_param('layers',updated);
                this.tab.parameter_changed();this.update();
            };
            for(const [key,label,min,max,step] of [['start','Start (s)',0,4,0.01],['gain','Level',0,1,0.05],['pitch','Pitch (st)',-12,12,1]]) {
                const wrapper=document.createElement('label');wrapper.textContent=label;
                const input=document.createElement('input');input.type='number';input.min=min;input.max=max;input.step=step;
                input.value=Number(layer[key].toFixed(2));input.setAttribute('aria-label',`${label} for layer ${index+1}`);
                input.addEventListener('change',()=>change(key,+input.value));wrapper.appendChild(input);row.appendChild(wrapper);
            }
            const remove=document.createElement('button');remove.textContent='×';remove.title='Remove layer '+(index+1);
            remove.setAttribute('aria-label',remove.title);remove.addEventListener('click',()=>{
                const updated=synth.get_layers();updated.splice(index,1);synth.set_param('layers',updated);
                this.tab.parameter_changed();this.update();
            });row.appendChild(remove);this.rows.appendChild(row);
            const track=document.createElement('div');track.className='stack-track';
            const bar=document.createElement('span');bar.textContent=(index+1)+' · '+layer.name;
            bar.style.marginLeft=(layer.start*synth.params.spacing/extent*100)+'%';
            bar.style.width=Math.max(3,Math.min(100-layer.start*synth.params.spacing/extent*100,(synth.layer_durations?.[index]||1)/extent*100))+'%';
            bar.style.backgroundColor=['#987849','#6d8370','#80718f','#9c6558','#647d8e','#8e864e'][index];
            track.appendChild(bar);this.timeline.appendChild(track);
        });
        if (!layers.length) this.timeline.textContent='Choose a preset, or add a sound below.';
        else {
            const scale=document.createElement('small');scale.textContent='0 s → '+extent.toFixed(2)+' s';this.timeline.appendChild(scale);
        }
        const selected=this.source.value;this.source.replaceChildren();
        for(const sourceTab of tabs) {
            if(sourceTab.name==='Stackr')continue;
            sourceTab.files.forEach((file,index)=>{
                const option=document.createElement('option');option.value=sourceTab.name+':'+index;
                option.textContent=sourceTab.name+' · '+file[0];this.source.appendChild(option);
            });
        }
        if([...this.source.options].some(option=>option.value===selected))this.source.value=selected;
        this.add.disabled=layers.length>=6 || !this.source.options.length;
        this.lock.textContent=synth.locked_param('layers')?'Unlock layers':'Lock layers';
        this.lock.setAttribute('aria-pressed',String(synth.locked_param('layers')));
    }
}
