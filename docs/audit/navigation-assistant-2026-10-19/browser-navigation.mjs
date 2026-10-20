import {createRequire} from 'node:module'
import {writeFile} from 'node:fs/promises'
const require=createRequire('C:/Users/Sodaa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/package.json'),{chromium}=require('playwright')
const phase=process.argv[2]??'after',base='http://127.0.0.1:5200',out='E:/Learning/xiliu/docs/audit/navigation-assistant-2026-10-19/'
const browser=await chromium.launch({headless:true,channel:'msedge'}),context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'}),page=await context.newPage(),errors=[]
page.on('pageerror',e=>errors.push(e.message))
await context.addInitScript(()=>{localStorage.setItem('xiliu-home-theme-v1','original');localStorage.setItem('xiliu-guide-v1',JSON.stringify({version:2,status:'dismissed',step:0}))})
const pref=await(await fetch(base+'/api/settings/preferences')).json();await fetch(base+'/api/settings/preferences',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_revision:pref.revision,changes:{theme:'light',fontSize:'small',displayName:'Soda'}})})
const rectangles=[]
for(const route of ['today','assistant','feed','inbox','knowledge','plans']){
 await page.goto(base+'/'+route);await page.waitForTimeout(900);await page.screenshot({path:out+phase+'-'+route+'.png'})
 if(phase==='after')rectangles.push({route,toolbar:await page.locator('.page-toolbar').first().boundingBox(),rail:await page.locator('.global-sidebar').boundingBox(),overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)})
 if(route==='today'){await page.getByRole('button',{name:'山水工作台',exact:true}).click();await page.waitForTimeout(300);await page.screenshot({path:out+phase+'-workbench.png'});if(phase==='after'){rectangles.push({route:'workbench',toolbar:await page.locator('.page-toolbar').boundingBox(),search:await page.getByRole('textbox',{name:'搜索息流'}).boundingBox()});await page.setViewportSize({width:390,height:844});await page.screenshot({path:out+'after-workbench-mobile.png'});await page.setViewportSize({width:1440,height:900})}}
}
await writeFile(out+phase+'-layout.json',JSON.stringify({errors,rectangles},null,2));await browser.close();console.log(JSON.stringify({phase,errors,rectangles},null,2))
