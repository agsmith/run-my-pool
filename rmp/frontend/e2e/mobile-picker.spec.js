const {test,expect}=require('@playwright/test');
const pool={id:'mobile-pool',name:'Sunday Football Club with a longer pool name',pool_type:'survivor',owner_id:'owner',is_private:true};
const name='Taller Napoleon 4 with a longer entry name';
const game={start_time:'2026-09-13T17:00:00Z',away_team:{id:1,name:'Buffalo Bills',abbrv:'BUF',logo:'/nfl/buf.svg'},home_team:{id:2,name:'Miami Dolphins',abbrv:'MIA',logo:'/nfl/mia.svg'}};
async function fixture(page){
 await page.addInitScript(()=>localStorage.setItem('session_expires_at',String(Date.now()+86400000)));
 await page.route('**/*',async route=>{
  const req=route.request(),p=new URL(req.url()).pathname;
  if(!['fetch','xhr'].includes(req.resourceType())||p.includes('/_next/'))return route.continue();
  let data={};
  if(p.endsWith('/auth/me'))data={id:'demo',email:'demo@example.com'};
  else if(p.endsWith('/my-pools'))data=[pool];
  else if(p.endsWith('/lock-status'))data={weeks:{1:{locked:false}}};
  else if(p.endsWith('/activity-summary'))data={week:1,entries_remaining:1,total_entries:1,week_selections:0};
  else if(p.endsWith('/picks-summary'))data={1:{teams:{},unlockedCount:1}};
  else if(p.includes('/entries/pool/'))data=[{id:'entry-1',name,alive:true}];
  else if(p.includes('/picks/entry/')||p.endsWith('/breakdown'))data=[];
  else if(p.includes('/schedule/week/'))data=Array.from({length:16},(_,i)=>({...game,game_id:i+1}));
  else if(p.endsWith('/picks/create'))data={id:'saved',...req.postDataJSON(),locked:false};
  else if(p.endsWith('/mobile-pool'))data=pool;
  return route.fulfill({json:data});
 });
}
async function fits(page){
 const result=await page.evaluate(()=>{
  const vv=window.visualViewport,save=[...document.querySelectorAll('button')].find(e=>e.textContent.trim()==='Save Pick'),dialog=document.querySelector('[aria-labelledby="entry-matchups-title"]');
  const s=save.getBoundingClientRect(),d=dialog.getBoundingClientRect();
  const topElement=document.elementFromPoint(d.left+d.width/2,d.top+20);
  return {onTop:dialog.contains(topElement),visible:s.top>=vv.offsetTop&&s.bottom<=vv.offsetTop+vv.height+1&&s.left>=vv.offsetLeft&&s.right<=vv.offsetLeft+vv.width+1,contained:d.left>=vv.offsetLeft&&d.right<=vv.offsetLeft+vv.width+1,width:document.documentElement.scrollWidth,viewport:innerWidth};
 });
 expect(result.visible,JSON.stringify(result)).toBe(true);expect(result.contained).toBe(true);expect(result.onTop).toBe(true);expect(result.width).toBeLessThanOrEqual(result.viewport);
}
for(const size of [{width:320,height:568},{width:390,height:664},{width:844,height:390}]){
 test(`full week picker fits ${size.width}x${size.height} and enlarged text`,async({page},testInfo)=>{
  await page.setViewportSize(size);await fixture(page);
  await page.goto('/pool/mobile-pool/entries');
  if(size.width<=650)await page.getByRole('button',{name:`Make week 1 pick for ${name}`,exact:true}).click();
  else await page.locator('.entries-season-table__week button').first().click();
  await expect(page.locator('.entries-overlay__game')).toHaveCount(16);
  await fits(page);
  await page.locator('.entries-overlay__content').evaluate(e=>{e.scrollTop=e.scrollHeight;});
  await fits(page);
  await page.evaluate(()=>document.documentElement.style.fontSize='20px');
  await fits(page);
  await page.locator('.entries-overlay__content').evaluate(e=>{e.scrollTop=0;});
  await page.getByRole('button',{name:'Buffalo Bills',exact:true}).first().click();
  await fits(page);
  if(size.width===390)await page.screenshot({path:testInfo.outputPath('safari-picker.png')});
  await page.getByRole('button',{name:'Save Pick',exact:true}).click();
  await expect(page.getByRole('dialog',{name:/Matchups/})).toHaveCount(0);
 });
}
test('picker follows a reduced visible viewport and restores on resize',async({page})=>{
 await page.setViewportSize({width:390,height:844});await fixture(page);
 await page.addInitScript(()=>{
  const viewport=new EventTarget();Object.assign(viewport,{height:560,width:390,offsetTop:60,offsetLeft:0,scale:1});
  Object.defineProperty(window,'visualViewport',{value:viewport,configurable:true});
 });
 await page.goto('/pool/mobile-pool/entries');
 await page.getByRole('button',{name:`Make week 1 pick for ${name}`,exact:true}).click();
 await expect(page.locator('.entries-overlay__game')).toHaveCount(16);await fits(page);
 await page.evaluate(()=>{Object.assign(visualViewport,{height:720,offsetTop:0});visualViewport.dispatchEvent(new Event('resize'));});
 await fits(page);
});
for(const width of [320,390]){
 test(`main pages fit at ${width}px with longer names and enlarged text`,async({page})=>{
  await page.setViewportSize({width,height:664});await fixture(page);
  for(const path of ['/dashboard','/pool/mobile-pool/entries','/pool/mobile-pool/matchups']){
   await page.goto(path, { waitUntil: 'networkidle' });
   await expect(page.locator('.workspace-hero h1')).toBeVisible();
   if(path==='/dashboard')await expect(page.locator('.pool-card')).toHaveCount(1);
   if(path.endsWith('/entries'))await expect(page.locator('.entries-mobile__card')).toHaveCount(1);
   if(path.endsWith('/matchups'))await expect(page.locator('.matchup-card')).toHaveCount(16);
   await page.evaluate(()=>document.documentElement.style.fontSize='20px');
   expect(await page.evaluate(()=>document.documentElement.scrollWidth),path).toBeLessThanOrEqual(width);
  }
 });
}

test('Pool Home reveals team counts and individual entries on a narrow phone', async ({page}) => {
 await page.setViewportSize({width:320,height:568});await fixture(page);
 await page.route('**/breakdown',route=>route.fulfill({json:[{team:'SEA',team_name:'Seattle Seahawks',count:2,entries:[{entry_id:'1',entry_name:name},{entry_id:'2',entry_name:'Seattle Two'}]},{team:'NE',team_name:'New England Patriots',count:1,entries:[{entry_id:'3',entry_name:'New England One'}]}]}));
 await page.goto('/pool/mobile-pool');
 await expect(page.getByText('Seattle Seahawks',{exact:true})).toBeVisible();
 await page.getByText('Seattle Seahawks',{exact:true}).click();
 await expect(page.getByText(name,{exact:true})).toBeVisible();
 await page.evaluate(()=>document.documentElement.style.fontSize='20px');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('.pick-breakdown').screenshot({path:'/tmp/rmp-pool-home-breakdown.png'});
});

test('save rejection is visible beside Save on a narrow phone', async ({page}) => {
 await page.setViewportSize({width:320,height:568});await fixture(page);
 await page.route('**/picks/create',route=>route.fulfill({status:423,json:{detail:'This pick is locked. The game has started or the pool lock time has passed.'}}));
 await page.goto('/pool/mobile-pool/entries');
 await page.getByRole('button',{name:`Make week 1 pick for ${name}`,exact:true}).click();
 await page.locator('.entries-team-option').first().click();
 await page.getByRole('button',{name:'Save Pick',exact:true}).click();
 const alert=page.getByRole('dialog').getByRole('alert');
 await expect(alert).toContainText('This pick is locked.');
 await expect(alert).toBeVisible();
 await fits(page);
 const bounds=await alert.boundingBox();expect(bounds.y).toBeGreaterThanOrEqual(0);expect(bounds.y+bounds.height).toBeLessThanOrEqual(568);
 await page.screenshot({path:'/tmp/rmp-picker-error-phone.png'});
});
