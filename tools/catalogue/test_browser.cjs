const {test} = require('node:test');
const assert = require('node:assert/strict');
const view = require('./browser_logic.js');
const row = (i, fields = {}) => ({id: String(i),path: `library/${i}.wav`,library:'games',description:`Sound ${i}`,category:null,catid:null,classification_status:'unclassified',duration:1, ...fields});

test('measured traits filter recordings and category counts without labelling them',()=>{
  const rows=[row(1,{acoustic_traits:['tonal_dominant']}),row(2),row(3,{category:'GAMES',acoustic_traits:['brief']})];
  const filter={trait:'tonal_dominant'};
  assert.deepEqual(view.filterRows(rows,filter).map(r=>r.id),['1']);
  assert.equal(view.categoryCounts(rows,filter).get('Unclassified'),1);
  assert.equal(view.filterRows(rows,filter)[0].category,null);
});

test('every one of 8407 unclassified entries can be reached without gaps', () => {
  const rows = Array.from({length:8407}, (_,i)=>row(i));
  const filtered = view.filterRows(rows,{category:'Unclassified'});
  assert.equal(view.paginate(filtered,0).totalPages,169);
  const ids=[];
  for(let page=0;page<169;page++) ids.push(...view.paginate(filtered,page).items.map(r=>r.id));
  assert.deepEqual(ids,rows.map(r=>r.id));
  const last=view.paginate(filtered,168);
  assert.equal(last.first,8401);assert.equal(last.last,8407);
  assert.equal(last.canNext,false);assert.equal(last.canPrevious,true);
});
test('category counts reflect selected library, search, duration and content',()=>{
  const rows=[row(1),row(2),row(3,{library:'valentino',description:'Fizz',content:'sfx'}),row(4,{library:'valentino',description:'Fizz long',content:'sfx',duration:30})];
  const filters={category:'Unclassified',library:'valentino',query:'fizz',length:'short',content:'sfx'};
  assert.equal(view.categoryCounts(rows,filters).get('Unclassified'),1);
  assert.equal(view.filterRows(rows,filters).length,1);
  assert.equal(view.paginate(view.filterRows(rows,filters),0).totalPages,1);
});
test('clearing other filters retains category and exposes every page',()=>{
  const rows=Array.from({length:103},(_,i)=>row(i,{library:i<3?'valentino':'games'}));
  const narrowed=view.filterRows(rows,{category:'Unclassified',library:'valentino'});
  assert.equal(narrowed.length,3);
  const cleared=view.filterRows(rows,{category:'Unclassified'});
  assert.equal(cleared.length,103);assert.equal(view.paginate(cleared,0).totalPages,3);
});
test('subcategory and classification filters also affect sidebar counts',()=>{
  const rows=[row(1,{category:'DOORS',catid:'DOORWood',classification_status:'provisional'}),row(2,{category:'DOORS',catid:'DOORMetl',classification_status:'provisional'}),row(3)];
  const counts=view.categoryCounts(rows,{leaf:'DOORWood',status:'provisional'});
  assert.equal(counts.get('DOORS'),1);assert.equal(counts.get('Unclassified'),undefined);
});
test('pagination clamps after filters change and zero matches has zero pages',()=>{
  assert.equal(view.paginate([row(1)],168).page,0);
  assert.equal(view.paginate([],0).totalPages,0);
  assert.equal(view.paginate([],0).canNext,false);
  assert.equal(view.paginate([row(1)],-10).page,0);
});
test('a duplicate with the matching label is not lost when canonical is filtered out',()=>{
  const rows=[row(1,{path:'original.wav'}),row(2,{path:'copy.wav',duplicate_of:'original.wav',category:'DOORS',catid:'DOORWood',classification_status:'provisional'})];
  assert.equal(view.filterRows(rows,{category:'DOORS'})[0].path,'copy.wav');
  assert.equal(view.filterRows(rows,{}).length,1);
  assert.equal(view.filterRows(rows,{showDuplicates:true}).length,2);
});
test('all descriptions in a selected multi-effect track survive deduplication',()=>{
  const rows=[row(1,{path:'track.wav'}),row(2,{path:'track.wav'}),row(3,{path:'copy.wav',duplicate_of:'track.wav'})];
  assert.equal(view.filterRows(rows,{}).length,2);
  assert.equal(view.categoryCounts(rows,{}).get('Unclassified'),1);
});
