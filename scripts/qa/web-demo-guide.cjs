const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||path.join(require('node:os').homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const base=process.env.DEMO_URL||'http://127.0.0.1:5184';
const output=path.resolve(__dirname,'../../.preview/web-demo-tour');fs.mkdirSync(output,{recursive:true});
const report={checks:[],errors:[],apiRequests:[]};
const check=(name,value)=>{report.checks.push({name,passed:Boolean(value)});if(!value)throw new Error(name)};
(async()=>{
const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
context.on('page',page=>{page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))report.apiRequests.push(r.url())})});
const page=await context.newPage();page.setDefaultTimeout(12000);
const shot=async name=>page.screenshot({path:path.join(output,name+'.png'),fullPage:true});
try{
 await page.goto(base+'/plans');await page.getByRole('dialog',{name:'欢迎使用息流',exact:true}).waitFor();
 check('first visit opens welcome automatically',true);await shot('welcome');
 check('background is inert during tour',await page.locator('#root').evaluate(el=>el.inert));
 await page.getByRole('button',{name:'下一步',exact:true}).click();
 await page.locator('.onboarding-spotlight').waitFor();await page.waitForURL('**/today');
 check('tour reveals the actual module and spotlight',await page.getByRole('dialog',{name:'今日',exact:true}).isVisible());
 await page.getByRole('button',{name:'下一步',exact:true}).click();await page.waitForURL('**/feed');await page.locator('.feed-card').first().waitFor();await shot('feed');
 await page.getByRole('button',{name:'上一步',exact:true}).click();await page.waitForURL('**/today');
 await page.getByRole('button',{name:'跳过引导',exact:true}).click();await page.waitForURL('**/plans');
 check('skipping restores the starting route',true);
 await page.reload();check('skipped tour stays closed on reload',await page.getByRole('dialog').count()===0);
 check('no independent wiki navigation remains',await page.locator('a[href^="/guide"]').count()===0);
 await page.getByRole('button',{name:'重新查看新手引导',exact:true}).click();
 await page.getByRole('dialog',{name:'欢迎使用息流',exact:true}).waitFor();
 const seen=[];
 for(let step=0;step<12;step++){
   const tooltip=page.locator('.onboarding-tooltip');await tooltip.waitFor();
   seen.push(await tooltip.getAttribute('aria-label'));
   if(step>0)await page.locator('.onboarding-spotlight').waitFor();
   if(step===7){await page.locator('[data-onboarding="settings-model"]').waitFor();await shot('model');}
   if(step===8){await page.setViewportSize({width:390,height:844});await page.locator('[data-onboarding="settings-appearance"]').waitFor();
     await page.waitForFunction(()=>{const r=document.querySelector('.onboarding-tooltip').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight});
     check('resizing to mobile keeps the tooltip inside viewport',true);await shot('mobile');
     await page.evaluate(()=>document.documentElement.dataset.theme='dark');await shot('dark');
     await page.keyboard.press('Tab');check('keyboard focus stays in the tour',await page.evaluate(()=>Boolean(document.activeElement.closest('.onboarding-tooltip'))));
     await page.setViewportSize({width:1440,height:1000});
   }
   const finish=tooltip.getByRole('button',{name:'开始使用',exact:true});
   if(await finish.count()){await finish.click();break}
   await tooltip.getByRole('button',{name:'下一步',exact:true}).click();
 }
 check('next alone introduces all main modules and settings',JSON.stringify(seen)===JSON.stringify(['欢迎使用息流','今日','资讯','收件箱','知识库','助手','个人计划','模型连接','外观与桌宠','自动任务','个人资料与数据','随时重新查看']));
 await page.waitForURL('**/plans');
 check('finish restores original route and releases focus lock',!(await page.locator('#root').evaluate(el=>el.inert)));
 await page.reload();check('completed tour stays closed on reload',await page.getByRole('dialog').count()===0);
 await page.getByRole('button',{name:'重新查看新手引导',exact:true}).click();await page.keyboard.press('Escape');
 check('Escape dismisses the tour',await page.getByRole('dialog').count()===0);
 await page.goto(base+'/feed');const card=page.locator('.feed-card').filter({hasText:'建立一个能持续使用的个人知识库'});
 await card.getByRole('button',{name:'收藏',exact:true}).click();await card.getByRole('button',{name:'已收进收件箱',exact:true}).waitFor();
 await page.goto(base+'/inbox');await page.getByRole('button',{name:'建立一个能持续使用的个人知识库',exact:true}).click();
 await page.getByRole('button',{name:'编辑',exact:true}).click();await page.getByLabel('标签',{exact:true}).fill('学习, 导览验收');
 await page.getByRole('button',{name:'保存修改',exact:true}).click();await page.locator('.content-row').filter({has:page.getByRole('button',{name:'建立一个能持续使用的个人知识库',exact:true})}).getByRole('button',{name:'归档到知识库',exact:true}).click();
 await page.goto(base+'/knowledge?folder=all');await page.getByRole('button',{name:'建立一个能持续使用的个人知识库',exact:true}).click();
 await page.getByRole('dialog',{name:'建立一个能持续使用的个人知识库',exact:true}).getByRole('button',{name:'引用提问',exact:true}).click();await page.getByRole('button',{name:'发送消息',exact:true}).click();
 await page.locator('.messages-scroll').getByText('演示回复',{exact:true}).first().waitFor();
 check('demo save edit archive and referenced reply remain usable',true);
 check('normal guide progress is untouched',await page.evaluate(()=>localStorage.getItem('xiliu-guide-v1')===null));
 check('no real API network requests',report.apiRequests.length===0);check('no browser errors',report.errors.length===0);
 report.status='passed';
}catch(error){report.status='failed';report.failure=error.stack;process.exitCode=1;await shot('failure').catch(()=>{});}
finally{fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
