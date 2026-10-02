class MixEditor {
    constructor(tab,parent) {
        this.tab=tab;
        this.root=document.createElement('section');this.root.className='mix-editor';
        parent.appendChild(this.root);
        this.rows=[0,1].map(slot=>{
            const row=document.createElement('div');row.className='mix-slot';
            const label=document.createElement('label');label.textContent=slot===0?'A':'B';
            const select=document.createElement('select');select.setAttribute('aria-label','Sound '+label.textContent);
            select.addEventListener('change',()=>{
                if(select.value==='empty')tab.synth.set_source(slot,null);
                else if(select.value!=='current'){
                    const [name,index]=select.value.split(':');
                    const sourceTab=tabs.find(t=>t.name===name),file=sourceTab&&sourceTab.files[+index];
                    if(!file)return;
                    const source=Stackr.source(name);source.apply_params(JSON.parse(file[1]));
                    tab.synth.set_source(slot,source,file[0]);
                }
                tab.parameter_changed();
            });
            label.appendChild(select);row.appendChild(label);
            const reseed=document.createElement('button');reseed.textContent='Reseed';
            reseed.setAttribute('aria-label','Reseed sound '+(slot===0?'A':'B'));
            reseed.addEventListener('click',()=>{tab.synth.reseed_source(slot);tab.parameter_changed();});
            row.appendChild(reseed);this.root.appendChild(row);
            return {select,reseed};
        });
        const clear=document.createElement('button');clear.textContent='Clear';
        clear.addEventListener('click',()=>{tab.synth.set_param('sources',[]);tab.parameter_changed();});
        this.root.appendChild(clear);
        this.root.addEventListener('keydown',event=>event.stopPropagation());
        this.update();
    }
    update() {
        const sources=this.tab.synth.get_sources();
        this.rows.forEach(({select,reseed},slot)=>{
            select.replaceChildren();
            const option=(value,text)=>{const o=document.createElement('option');o.value=value;o.textContent=text;select.appendChild(o);};
            option('empty','Choose a sound…');
            if(sources[slot])option('current',sources[slot].synth+' · '+sources[slot].name);
            for(const sourceTab of tabs){
                if(sourceTab.name==='Mixr'||sourceTab.name==='Stackr')continue;
                const group=document.createElement('optgroup');group.label=sourceTab.synth.display_name||sourceTab.name;
                sourceTab.files.forEach((file,index)=>{const o=document.createElement('option');o.value=sourceTab.name+':'+index;o.textContent=file[0];group.appendChild(o);});
                select.appendChild(group);
            }
            select.value=sources[slot]?'current':'empty';
            reseed.disabled=!sources[slot];
        });
    }
}
