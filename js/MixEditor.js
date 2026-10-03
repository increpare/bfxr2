class MixEditor {
    constructor(tab,parent) {
        this.tab=tab;
        this.catalog=Mixr.generators().filter((entry,index,entries)=>
            index===0 || entry.synth!==entries[index-1].synth);
        this.root=document.createElement('section');this.root.className='mix-editor';
        parent.appendChild(this.root);
        this.rows=[0,1].map(slot=>{
            const row=document.createElement('div');row.className='mix-slot';
            const label=document.createElement('label');label.textContent=slot===0?'A':'B';
            const select=document.createElement('select');select.setAttribute('aria-label','Synth '+label.textContent);
            select.addEventListener('change',()=>{
                if(select.value==='empty')tab.synth.set_source(slot,null);
                else tab.synth.set_generator(slot,select.value,'*');
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
            option(select,'empty','Choose a synth…');
            const current=sources[slot];
            if(current&&!this.catalog.some(entry=>entry.synth===current.synth))
                option(select,current.synth,synth_display_name(current.synth));
            for(const entry of this.catalog)option(select,entry.synth,entry.family);
            select.title=current ? synth_display_name(current.synth)+' · '+current.name : '';
            select.value=current?current.synth:'empty';
            regen.disabled=!current || !current.generator || this.tab.synth.locked_param('sources');
        });
        this.both.disabled=this.rows.every(row=>row.regen.disabled);
    }
}
