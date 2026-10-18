<script lang="ts">
  import type { RuntimeConfig } from '../definition.generated';
  import { clone } from '../model';
  let { runtime, prefix, onchange, onprefix }: {runtime: RuntimeConfig; prefix:string; onchange:(value:RuntimeConfig)=>void; onprefix:(value:string)=>void} = $props();
  function set(patch:Partial<RuntimeConfig>) { onchange({...runtime,...patch}); }
  function update(field:'hooks'|'schedules', index:number, patch:Record<string,unknown>) {
    const next = clone(runtime);
    if (field === 'hooks') next.hooks = next.hooks?.map((item,i)=>i===index?{...item,...patch}:item);
    else next.schedules = next.schedules?.map((item,i)=>i===index?{...item,...patch}:item);
    onchange(next);
  }
  function setting(old:string, name:string, value: string|number|boolean) {
    const defaults = {...runtime.settings?.defaults}; delete defaults[old]; defaults[name]=value;
    set({settings:{...runtime.settings,defaults}});
  }
</script>
<section class="bot-settings glass" aria-label="Bot configuration">
  <details>
    <summary>Bot configuration & features</summary>
    <div class="feature-grid">
      <section><h3>Gateway & presence</h3>
        <label>Command prefix<input maxlength="10" value={prefix} onchange={e=>onprefix(e.currentTarget.value)}/></label>
        <label>Playing status<input maxlength="128" value={runtime.presence || ''} onchange={e=>set({presence:e.currentTarget.value})}/></label>
        <label>Availability<select value={runtime.status || 'online'} onchange={e=>set({status:e.currentTarget.value as RuntimeConfig['status']})}><option>online</option><option>idle</option><option>dnd</option><option>invisible</option></select></label>
        <label class="checkbox-label"><input type="checkbox" checked={runtime.message_content} onchange={e=>set({message_content:e.currentTarget.checked})}/> Message content intent</label>
        <label class="checkbox-label"><input type="checkbox" checked={runtime.members} onchange={e=>set({members:e.currentTarget.checked})}/> Server members intent</label>
        <p class="micro">Prefix commands and message hooks enable message content automatically. Member hooks enable members automatically. Enable privileged intents in Discord too.</p>
        <h3>Allowed mentions</h3>
        {#each [{key:'mention_users',label:'Allow user mentions'},{key:'mention_roles',label:'Allow role mentions'},{key:'mention_everyone',label:'Allow everyone mentions'}] as item}
          <label class="checkbox-label"><input type="checkbox" checked={Boolean(runtime[item.key as keyof RuntimeConfig])} onchange={e=>set({[item.key]:e.currentTarget.checked})}/>{item.label}</label>
        {/each}
      </section>
      <section><h3>Help & command packs</h3>
        <label class="checkbox-label"><input type="checkbox" checked={runtime.help} onchange={e=>set({help:e.currentTarget.checked})}/> Searchable command help</label>
        <label>Commands per help page<input type="number" min="1" max="10" value={runtime.help_page_size || 6} onchange={e=>set({help_page_size:+e.currentTarget.value})}/></label>
        {#each ['polls','reminders','moderation'] as pack}
          <label class="checkbox-label"><input type="checkbox" checked={runtime.packs?.some(p=>p===pack)} onchange={e=>set({packs:(e.currentTarget.checked?[...(runtime.packs || []),pack]:(runtime.packs || []).filter(p=>p!==pack)) as RuntimeConfig['packs']})}/>{pack}</label>
        {/each}
        <p class="micro">Help adds /help with search, category dropdowns and page buttons. Packs register built-in commands. Moderation always requires confirmation and permission/hierarchy checks; the timeout pack uses 10 minutes.</p>
        <p class="micro">Only built-in packs run in the visual builder. Custom Python plugins remain available through the Python API.</p>
      </section>
      <section class="feature-wide"><h3>Event hooks</h3>
        {#each runtime.hooks || [] as hook,index}
          <div class="feature-card">
            <label>Event<select value={hook.event} onchange={e=>update('hooks',index,{event:e.currentTarget.value})}><option value="message">Message trigger</option><option value="member_join">Member greeting / auto-role</option><option value="reaction_add">Reaction added (cached messages)</option></select></label>
            <label>Match text or emoji<input value={hook.match} onchange={e=>update('hooks',index,{match:e.currentTarget.value})}/></label>
            <label>Hook channel ID<input inputmode="numeric" value={hook.channel_id || ''} onchange={e=>update('hooks',index,{channel_id:e.currentTarget.value || null})}/></label>
            {#if hook.event==='member_join'}<label>Auto-role ID (optional)<input inputmode="numeric" value={hook.role_id || ''} onchange={e=>update('hooks',index,{role_id:e.currentTarget.value || null})}/></label>{/if}
            <label>Hook response<textarea rows="2" value={hook.response} onchange={e=>update('hooks',index,{response:e.currentTarget.value})}></textarea></label>
            {#if hook.event==='message'}<label class="checkbox-label"><input type="checkbox" checked={hook.exact} onchange={e=>update('hooks',index,{exact:e.currentTarget.checked})}/> Match whole message</label>{/if}
            <button class="text-button danger" onclick={()=>set({hooks:runtime.hooks?.filter((_,i)=>i!==index)})}>Remove hook</button>
          </div>
        {/each}
        <button class="button secondary compact" onclick={()=>set({hooks:[...(runtime.hooks || []),{event:'message',match:'hello bot',response:'Hello, {{user.display_name}}!',exact:true}]})}>Add event hook</button>
      </section>
      <section><h3>Server settings</h3>
        <label>Settings schema version<input type="number" min="1" max="1000" value={runtime.settings?.version || 1} onchange={e=>set({settings:{...runtime.settings,version:+e.currentTarget.value}})}/></label>
        {#each Object.entries(runtime.settings?.defaults || {}) as [name,value]}
          <div class="feature-card">
            <label>Setting name<input value={name} onchange={e=>setting(name,e.currentTarget.value,value)}/></label>
            <label>Default type<select value={typeof value} onchange={e=>setting(name,name,e.currentTarget.value==='boolean'?false:e.currentTarget.value==='number'?0:'')}><option value="string">Text</option><option value="number">Number</option><option value="boolean">Boolean</option></select></label>
            <label>Default value<input value={String(value)} onchange={e=>setting(name,name,typeof value==='boolean'?e.currentTarget.value==='true':typeof value==='number'?Number(e.currentTarget.value):e.currentTarget.value)}/></label>
            <button class="text-button danger" onclick={()=>{const defaults={...runtime.settings?.defaults};delete defaults[name];set({settings:{...runtime.settings,defaults}});}}>Remove setting</button>
          </div>
        {/each}
        <button class="button secondary compact" onclick={()=>setting('',`setting_${Object.keys(runtime.settings?.defaults || {}).length+1}`,'')}>Add server setting</button>
        <p class="micro">Reference defaults as {'{{settings.name}}'}. Stored values are isolated by server. Schema changes require a higher version and migrations for renamed keys.</p>
        <details><summary>Settings migrations</summary>
          {#each runtime.settings?.migrations || [] as migration,index}
            <div class="feature-card">
              <label>From version<input type="number" min="1" value={migration.from_version} onchange={e=>set({settings:{...runtime.settings,migrations:runtime.settings?.migrations?.map((m,i)=>i===index?{...m,from_version:+e.currentTarget.value}:m)}})}/></label>
              <label>Rename keys (old=new, comma separated)<input value={Object.entries(migration.rename || {}).map(([a,b])=>`${a}=${b}`).join(', ')} onchange={e=>set({settings:{...runtime.settings,migrations:runtime.settings?.migrations?.map((m,i)=>i===index?{...m,rename:Object.fromEntries(e.currentTarget.value.split(',').map(pair=>pair.split('=').map(v=>v.trim())).filter(pair=>pair.length===2 && pair[0] && pair[1]))}:m)}})}/></label>
              <button class="text-button danger" onclick={()=>set({settings:{...runtime.settings,migrations:runtime.settings?.migrations?.filter((_,i)=>i!==index)}})}>Remove migration</button>
            </div>
          {/each}
          <button class="text-button" onclick={()=>set({settings:{...runtime.settings,migrations:[...(runtime.settings?.migrations || []),{from_version:1,rename:{}}]}})}>Add migration</button>
        </details>
      </section>
      <section><h3>Scheduled announcements</h3>
        {#each runtime.schedules || [] as job,index}
          <div class="feature-card">
            <label>Schedule ID<input value={job.id} onchange={e=>update('schedules',index,{id:e.currentTarget.value})}/></label>
            <label>Destination channel ID<input inputmode="numeric" value={job.channel_id} onchange={e=>update('schedules',index,{channel_id:e.currentTarget.value})}/></label>
            <label>Repeat every (seconds)<input type="number" min="60" value={job.seconds} onchange={e=>update('schedules',index,{seconds:+e.currentTarget.value})}/></label>
            <label>Retry attempts<input type="number" min="0" max="10" value={job.retries} onchange={e=>update('schedules',index,{retries:+e.currentTarget.value})}/></label>
            <label>Announcement<textarea rows="2" value={job.response} onchange={e=>update('schedules',index,{response:e.currentTarget.value})}></textarea></label>
            <button class="text-button danger" onclick={()=>set({schedules:runtime.schedules?.filter((_,i)=>i!==index)})}>Remove schedule</button>
          </div>
        {/each}
        <button class="button secondary compact" onclick={()=>set({schedules:[...(runtime.schedules || []),{id:`announcement_${(runtime.schedules || []).length+1}`,channel_id:'123456789',seconds:3600,retries:3,response:'Scheduled announcement'}]})}>Add scheduled announcement</button>
        <p class="micro">Jobs persist in bot storage and retry failures. Run one process per bot. Delivery is at least once; announcements may repeat after a crash.</p>
      </section>
    </div>
  </details>
</section>
