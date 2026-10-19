/* UI enhancement only. The existing forms and their handlers remain the source of truth. */
(() => {
 'use strict';
 const dialog=document.getElementById('main-dialog');
 if(!dialog||typeof MutationObserver==='undefined')return;
 const draft={name:'',symbol:'',logo:''};let stage='wallets',queued=false;
 const node=(tag,className,text)=>{const el=document.createElement(tag);if(className)el.className=className;if(text!==undefined)el.textContent=text;return el;};
 const setText=(el,value)=>{if(el&&el.textContent!==value)el.textContent=value;};
 const setImage=(el,value)=>{if(el&&el.getAttribute('src')!==value)el.setAttribute('src',value);};
 const observed={childList:true,subtree:true,attributes:true,attributeFilter:['class','open','src']};
 const watch=()=>observer.observe(dialog,observed);
 function captureDraft(){const form=dialog.querySelector('#live-setup');if(!form)return;draft.name=form.querySelector('[name="name"]')?.value.trim()||'';draft.symbol=form.querySelector('[name="symbol"]')?.value.trim().toUpperCase()||'';draft.logo=form.querySelector('#live-logo')?.getAttribute('src')||'';}
 function progress(view){const current=view==='setup'?0:view==='networks'?(stage==='wallets'?1:2):3;const list=node('ol','deploy-progress');list.setAttribute('aria-label','Launch setup progress');['Token details','Your wallets','Funding plan'].forEach((label,i)=>{const item=node('li');if(i===current)item.setAttribute('aria-current','step');if(i<current)item.dataset.complete='true';item.append(node('span','deploy-step-number',i<current?'✓':String(i+1)),node('span','',label));list.append(item);});return list;}
 function side(){const aside=node('aside','deploy-side');aside.setAttribute('aria-label','Token and funding summary');const inner=node('div','deploy-side-inner');inner.innerHTML='<p class="deploy-side-label">Your launch at a glance</p><div class="deploy-token-preview"><img class="deploy-token-art" width="82" height="82" alt="Token image preview"><h3 class="deploy-token-name"></h3><p class="deploy-token-ticker"></p><div class="deploy-chain-tags"><span><img src="/assets/solana.svg" alt="">Solana</span><span><img src="/assets/robinhood.svg" alt="">Robinhood</span></div></div><p class="deploy-side-caption">One identity across two independent tokens.</p><div class="deploy-costs" hidden><p class="deploy-side-label">Planned capital</p><div class="deploy-cost-line"><span>Solana</span><strong data-deploy-total="sol"></strong></div><div class="deploy-cost-line"><span>Robinhood</span><strong data-deploy-total="evm"></strong></div><p class="deploy-side-caption">Developer buy + 3× MM capital + MM gas reserve. Creator launch costs are additional.</p></div><div class="deploy-side-foot"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M12 3 4 6v6c0 4 4 7 8 9 4-2 8-5 8-9V6z"/><path d="m8.5 12 2.5 2.5 4.5-5"/></svg><span>Wallet approval is a separate step. Saving a plan does not move funds.</span></div>';aside.append(inner);return aside;}
 function updateSummary(){captureDraft();const art=dialog.querySelector('.deploy-token-art');setImage(art,draft.logo||'/assets/mascot.png?v=2');if(art)art.alt=draft.logo?'Token image preview':'Twice mascot';setText(dialog.querySelector('.deploy-token-name'),draft.name||'Your token');setText(dialog.querySelector('.deploy-token-ticker'),draft.symbol?'$'+draft.symbol:dialog.dataset.deployView==='review'?'Saved funding plan':'$TICKER');const totals=[...dialog.querySelectorAll('.deploy-main .funding-total strong')];const costs=dialog.querySelector('.deploy-costs');if(costs)costs.hidden=totals.length!==2;if(totals.length===2){setText(dialog.querySelector('[data-deploy-total="sol"]'),totals[0].textContent);setText(dialog.querySelector('[data-deploy-total="evm"]'),totals[1].textContent);}}
 function refreshCards(){for(const card of dialog.querySelectorAll('.deploy-network-card')){const address=card.querySelector('.wallet-row>span')?.textContent.trim();card.dataset.connected=String(!!address&&address!=='Not connected');}}
 function setStage(next,{focus=false}={}){
  stage=next;const form=dialog.querySelector('#live-networks');if(!form)return;
  const wallets=form.querySelector('.deploy-wallet-fields'),budget=form.querySelector('.deploy-budget-fields');if(!wallets||!budget)return;form.dataset.deployStage=stage;wallets.hidden=stage!=='wallets';budget.hidden=stage!=='funding';
  for(const input of budget.querySelectorAll('[data-deploy-required]'))input.required=stage==='funding';
  setText(dialog.querySelector('#dialog-title'),stage==='wallets'?'Connect your two worlds.':'Plan your launch capital.');
  setText(dialog.querySelector('.deploy-step-intro'),stage==='wallets'?'Choose the developer wallet for each chain. Connection alone does not transfer funds.':'Enter a developer buy on either chain. Twice matches the other amount and calculates your MM budget.');
  const old=dialog.querySelector('.deploy-progress');if(old)old.replaceWith(progress('networks'));
  const error=form.querySelector('.deploy-step-error');if(error)error.remove();updateSummary();
  if(focus){const title=dialog.querySelector('#dialog-title');title.tabIndex=-1;title.focus({preventScroll:true});dialog.scrollTop=0;}
 }
 function nextStep(){const form=dialog.querySelector('#live-networks');if(!form)return;refreshCards();const missing=[...form.querySelectorAll('.deploy-network-card')].filter(c=>c.dataset.connected!=='true');if(missing.length){let error=form.querySelector('.deploy-step-error');if(!error){error=node('p','deploy-step-error');error.setAttribute('role','alert');form.querySelector('.deploy-wallet-fields').append(error);}error.textContent='Connect both developer wallets before continuing to your funding plan.';missing[0].querySelector('.wallet-row button')?.focus();return;}setStage('funding',{focus:true});}
 function arrangeNetworks(form){
  if(form.dataset.deployArranged||!form.querySelector(':scope > .modal-actions')||!form.querySelector(':scope > .funding-panel'))return;form.dataset.deployArranged='true';const children=[...form.children];const wallets=node('section','deploy-wallet-fields'),grid=node('div','deploy-network-grid'),budget=node('section','deploy-budget-fields');wallets.setAttribute('aria-label','Developer wallets');budget.setAttribute('aria-label','Funding plan');wallets.append(grid);
  let card=null,actions=null;
  for(const child of children){
   if(child.classList.contains('chain-choice')){const platform=child.querySelector('input[type="hidden"]')?.value;card=node('section','deploy-network-card');card.dataset.platform=platform||'';const image=node('img','deploy-network-icon');image.src=platform==='pons'?'/assets/robinhood.svg':'/assets/solana.svg';image.alt='';image.width=32;image.height=32;child.prepend(image);card.append(child);grid.append(card);}
   else if(child.classList.contains('wallet-row')||child.classList.contains('field')){if(card)card.append(child);else wallets.append(child);}
   else if(child.classList.contains('funding-panel'))budget.append(child);
   else if(child.classList.contains('modal-actions'))actions=child;
   else wallets.append(child);
  }
  if(!actions)return;const submit=actions.querySelector('button:not([type="button"])');if(submit)submit.classList.add('deploy-funding-submit');
  const back=node('button','btn deploy-budget-back','Back to wallets');back.type='button';back.dataset.deployBack='true';const next=node('button','btn btn-primary deploy-wallet-next','Continue to funding');next.type='button';next.dataset.deployNext='true';actions.prepend(back);actions.append(next);
  for(const input of budget.querySelectorAll('[required]'))input.dataset.deployRequired='true';
  form.prepend(wallets,budget);form.append(actions);form.addEventListener('submit',e=>{if(stage==='wallets'){e.preventDefault();e.stopImmediatePropagation();nextStep();}},true);refreshCards();setStage(stage);
 }
 function decorate(){
  queued=false;observer.disconnect();
  try{
   if(!dialog.classList.contains('live-launch')){dialog.classList.remove('deploy-designed');delete dialog.dataset.deployView;return;}
   dialog.classList.add('deploy-designed');const content=dialog.querySelector('.dialog-content');if(!content)return;
   const setup=content.querySelector('#live-setup'),networks=content.querySelector('#live-networks');const view=setup?'setup':networks?'networks':content.querySelector('.funding-status')&&content.querySelector('.funding-chain')?'review':'general';dialog.dataset.deployView=view;
   if(!content.querySelector('.deploy-main')){
    if(view==='review'){const savedName=dialog.querySelector('#dialog-title')?.textContent.replace(/ · Funding plan$/,'')||'';if(savedName!==draft.name){draft.name=savedName;draft.symbol='';draft.logo='';}}
    if(view!=='general')setText(dialog.querySelector('.dialog-header small'),'TWICE / LAUNCH SETUP');
    if(setup){stage='wallets';captureDraft();setText(dialog.querySelector('#dialog-title'),'Give your token an identity.');const submit=setup.querySelector('button:not([type="button"])');if(submit)setText(submit,'Continue to wallets');const symbol=setup.querySelector('[name="symbol"]');if(symbol){symbol.autocapitalize='characters';symbol.spellcheck=false;}const website=setup.querySelector('[name="website"]');if(website){website.autocomplete='url';website.spellcheck=false;}}
    const main=node('div','deploy-main');while(content.firstChild)main.append(content.firstChild);content.append(main);
    if(view!=='general'){content.prepend(progress(view));content.append(side());}
    if(networks){const intro=node('p','deploy-step-intro');main.prepend(intro);arrangeNetworks(networks);}
   }
   if(networks)refreshCards();updateSummary();
  }finally{watch();}
 }
 function schedule(){if(!queued){queued=true;queueMicrotask(decorate);}}
 const observer=new MutationObserver(schedule);watch();
 dialog.addEventListener('input',()=>{captureDraft();updateSummary();});
 dialog.addEventListener('click',event=>{const target=event.target.closest('button');if(!target)return;if(target.dataset.deployNext){event.preventDefault();nextStep();}else if(target.dataset.deployBack){event.preventDefault();setStage('wallets',{focus:true});}});
 dialog.addEventListener('close',()=>{stage='wallets';draft.name='';draft.symbol='';draft.logo='';});
 schedule();
})();
