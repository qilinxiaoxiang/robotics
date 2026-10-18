const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/viewer.js','utf8');
function actual(name){const start=source.indexOf('function '+name+'(');assert(start>=0,name);const end=source.indexOf('\nfunction ',start+1);return source.slice(start,end<0?undefined:end);}
const ctx={DATA:{headPrototypeRevision:{status:'CURRENT_PRINT_PROTOTYPE_GUIDE',moduleFasteners:{electronics:[{spec:'M2 × 6 TAP',quantity:8,use:'Boards'},{spec:'M2.5 × 8 TAP',quantity:4,use:'Audio'}]}}},buildSection:'electronics',panel:{innerHTML:''},safe:s=>s,sourceFooter:()=>'',setSection:()=>{},$:()=>({})};
vm.createContext(ctx);
for(const name of ['currentHeadPrototypeSection','legacyHeadSection','displayModuleTitle','legacyHeadNotice','headPrototypeScrewPanel','fastenerRevisionSourceNote'])vm.runInContext(actual(name),ctx);
assert.equal(ctx.legacyHeadSection(),false);
assert.equal(ctx.displayModuleTitle({id:'electronics',title:'Populate the detached curved cap'}),'V1.5 prototype · Populate the detached curved cap');
const note=ctx.legacyHeadNotice();assert(note.includes('V1.5'));assert(!/Legacy|rooftop|superseded|HEAD-EYE-REVIEW/.test(note));assert(note.includes('USB'));
ctx.headPrototypeScrewPanel();assert(ctx.panel.innerHTML.includes('12 specified screws'));assert(ctx.panel.innerHTML.includes('M2 × 6 TAP'));assert(ctx.panel.innerHTML.includes('M2.5 × 8 TAP'));assert(!ctx.panel.innerHTML.includes('0 specified screws'));
ctx.DATA.fastenerRevision={};const footer=ctx.fastenerRevisionSourceNote();assert(footer.includes('V1.5'));assert(!footer.includes('V1.4'));assert(!footer.includes('旧版'));
const template=fs.readFileSync(__dirname+'/template.html','utf8');assert(!template.includes('HEAD-EYE-REVIEW'));assert(template.includes('V1.5 incremental print set'));assert(template.includes('href="/REPRINT-PLAN.html"'));
assert(source.includes("selectBuildSection('electronics');setSection('assembly')"));
ctx.buildSection='left-leg';assert(!ctx.currentHeadPrototypeSection());assert(!ctx.legacyHeadSection());assert.equal(ctx.displayModuleTitle({id:'left-leg',title:'Left leg'}),'Left leg');
ctx.buildSection='head';delete ctx.DATA.headPrototypeRevision;assert(ctx.legacyHeadSection());
console.log('HEAD_PROTOTYPE_LABELS_AND_FASTENER_PAGE_PASS');
