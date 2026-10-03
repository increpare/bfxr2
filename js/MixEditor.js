class MixEditor {
    constructor(tab,parent) {
        this.tab=tab;
        this.catalog=Mixr.generators();
        this.root=document.createElement('section');this.root.className='mix-editor';
        parent.appendChild(this.root);
        this.rows=[0,1].map(slot=>{
            const row=document.createElement('div');row.className='mix-slot';
            const label=document.createElement('label');label.textContent=slot===0?'A':'B';
            const select=document.createElement('select');select.setAttribute('aria-label','Preset '+label.textContent);
            select.addEventListener('change',()=>{
                if(select.value==='empty')tab.synth.set_source(slot,null);
                else if(select.value!=='current'){
                    const [name,generator]=select.value.split(':');
                    tab.synth.set_generator(slot,name,generator);
                }
                tab.parameter_changed();
            });
            label.appendChild(select);row.appendChild(label);
            const regen=document.createElement('button');regen.textContent='Regen';
            regen.setAttribute('aria-label','Regen '+(slot===0?'A':'B'));
            regen.addEventListener('click',()=>{tab.synth.regenerate_source(slot);tab.parameter_changed();});
            row.appendChild(regen);this.root.appendChild(row);
            return {select,regen};
        });
        this.both=document.createElement('button');this.both.textContent='Regen Both';
        this.both.addEventListener('click',()=>{tab.synth.regenerate_both();tab.parameter_changed();});
        this.root.appendChild(this.both);
        this.root.addEventListener('keydown',event=>event.stopPropagation());
        this.update();
    }
    update() {
        const sources=this.tab.synth.get_sources();
        this.rows.forEach(({select,regen},slot)=>{
            select.replaceChildren();
            const option=(parent,value,text)=>{const o=document.createElement('option');o.value=value;o.textContent=text;parent.appendChild(o);};
            option(select,'empty','Choose a preset…');
            const current=sources[slot];
            if(current&&!current.generator)option(select,'current',synth_display_name(current.synth)+' · '+current.name+' (saved sound)');
            let name;
            for(const entry of this.catalog){
                if(name!==entry.synth){
                    option(select,entry.synth+':*',entry.family);
                    name=entry.synth;
                }
                option(select,entry.synth+':'+entry.generator,'  '+entry.family+' · '+entry.name);
            }
            select.title=current ? synth_display_name(current.synth)+' · '+current.name : '';
            select.value=current?(current.generator?current.synth+':'+current.generator:'current'):'empty';
            regen.disabled=!current || !current.generator || this.tab.synth.locked_param('sources');
        });
        this.both.disabled=this.rows.every(row=>row.regen.disabled);
    }
}
