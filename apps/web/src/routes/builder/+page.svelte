<script lang="ts">
  import { onMount } from 'svelte';
  import { SvelteFlow, Background, Controls, MiniMap, type Node, type Edge as FlowEdge, type Connection } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import { Plus, ArrowRight, Play, Download, Upload, Undo2, Redo2, List, Workflow, Save, Trash2, Hash, MessageSquare, GitBranch, PanelTop, Check, X, Cloud, CircleHelp, Sparkles, LogOut } from '@lucide/svelte';
  import BotSettings from '../../lib/components/BotSettings.svelte';
  import AdvancedFields from '../../lib/components/AdvancedFields.svelte';
  import type { RuntimeConfig } from '../../lib/definition.generated';
  import FlowNode from '../../lib/components/FlowNode.svelte';
  import CanvasDrop from '../../lib/components/CanvasDrop.svelte';
  import { api, setCsrf } from '../../lib/api';
  import { clone, type Block, type Definition, type Project, type PreviewResult, type PreviewMessage } from '../../lib/model';
  import hello from '../../lib/hello.json';

  let definition = $state<Definition>(clone(hello) as unknown as Definition);
  let selectedId = $state('command-1');
  let selected = $derived(definition.nodes.find(node => node.id === selectedId));
  let flowNodes = $state<Node[]>([]);
  let flowEdges = $state<FlowEdge[]>([]);
  let undoStack = $state<Definition[]>([]);
  let redoStack = $state<Definition[]>([]);
  let listView = $state(false);
  let ready = $state(false);
  let templates = $state<Record<string, Definition>>({ greeting: clone(hello) as unknown as Definition });
  let user = $state<{ id: string; name: string; can_host: boolean } | null>(null);
  let config = $state({ dev_login: false, oauth_enabled: false, variables: ['user.display_name', 'server.name', 'channel.name'] });
  let projects = $state<Project[]>([]);
  let current = $state<Project | null>(null);
  let saved = $state(JSON.stringify(hello));
  let restoredProject = $state<{id: string; version: number; saved: string} | null>(null);
  let localSaved = $state(true);
  let error = $state('');
  let notice = $state('');
  let validation = $state('Checking…');
  let busy = $state(false);
  let preview = $state<PreviewResult | null>(null);
  let previewCommand = $state('command-1');
  let previewName = $state('Aaryan');
  let previewServer = $state('My server');
  let previewChannel = $state('general');
  let previewChannelId = $state('100000002');
  let previewRoles = $state('');
  let previewPermissions = $state('');
  let previewAgeRestricted = $state(false);
  let previewInServer = $state(true);
  let previewMode = $state('slash');
  let previewOptions = $state<Record<string,string>>({});
  let simulationState = $state({values:{},jobs:{}});
  let modalValues = $state<Record<string,string>>({});
  let hookIndex = $state('0');
  let hookMatch = $state('hello bot');
  let syncSnapshot = $state('[]');
  let syncDiff = $state<{scope:string;changes:{name:string;action:string;before:unknown;after:unknown}[]} | null>(null);
  const defaultRuntime = clone(hello.runtime) as unknown as RuntimeConfig;
  let showContext = $state(false);
  let credentials = $state(false);
  let token = $state('');
  let applicationId = $state('');
  let guildId = $state('');
  let revisions = $state<{id: string; created_at: number}[]>([]);
  let events = $state<{message: string; created_at: number}[]>([]);
  let fileInput: HTMLInputElement;
  const nodeTypes = { block: FlowNode };
  let triggers = $derived(definition.nodes.filter(node => node.kind === 'trigger'));
  let dirty = $derived(JSON.stringify(definition) !== saved);

  function summary(node: Block) {
    if (node.kind === 'trigger') return node.description || 'A bot command';
    if (node.kind === 'condition') return `${node.field === 'role' ? 'Has role' : 'In channel'} ${node.value}`;
    if (node.kind === 'embed') return node.description || 'Embed';
    if (node.kind === 'action') return node.operation || 'Server data';
    if (node.kind === 'form') return node.response || 'Collect user input';
    return node.content || 'Write your reply';
  }
  function label(node: Block) {
    if (node.kind === 'trigger') return `${node.mode === 'prefix' ? definition.prefix : '/'}${node.name}`;
    if (node.kind === 'condition') return 'Choose a path';
    if (node.kind === 'embed') return node.title || 'Rich embed';
    if (node.kind === 'message') return 'Interactive message';
    if (node.kind === 'form') return node.title || 'Form';
    if (node.kind === 'action') return 'Server action';
    return 'Send a reply';
  }
  $effect(() => {
    flowNodes = definition.nodes.map((node, index) => ({ id: node.id, type: 'block', position: definition.layout.positions[node.id] || { x: 80 + index * 300, y: 100 }, selected: node.id === selectedId, data: { terminal: node.kind==='form' || (node.kind==='action' && node.operation==='moderation'), kind: node.kind, label: label(node), summary: summary(node), step: String(index + 1).padStart(2, '0') } }));
    flowEdges = definition.edges.map(edge => ({ ...edge, sourceHandle: edge.branch || 'next', label: edge.branch === 'true' ? 'True' : edge.branch === 'false' ? 'False' : '', type: 'smoothstep', style: 'stroke: #8e8076; stroke-width: 1.5' }));
  });
  $effect(() => {
    const snapshot = JSON.stringify(definition);
    const project = current ? { id: current.id, version: current.version, saved } : restoredProject;
    if (!ready) return;
    let active = true;
    validation = 'Checking…';
    const timer = setTimeout(() => {
      try { localStorage.setItem('dbm-draft', JSON.stringify({ definition: JSON.parse(snapshot), project })); localSaved = true; }
      catch { localSaved = false; }
      api('/validate', 'POST', JSON.parse(snapshot))
        .then(() => { if (active) validation = ''; })
        .catch(cause => { if (active) validation = cause.message; });
    }, 450);
    return () => { active = false; clearTimeout(timer); };
  });

  onMount(() => {
    let active = true;
    try {
      const local = JSON.parse(localStorage.getItem('dbm-draft') || 'null');
      const draft = local?.definition;
      if (draft && Array.isArray(draft.nodes) && Array.isArray(draft.edges) && draft.layout?.positions && typeof draft.name === 'string') {
        definition = draft;
        selectedId = draft.nodes[0]?.id || '';
        previewCommand = draft.nodes.find((node: Block) => node.kind === 'trigger')?.id || '';
        if (local.project?.id && Number.isInteger(local.project.version) && typeof local.project.saved === 'string') restoredProject = local.project;
      }
    } catch { notice = 'Could not restore the previous local draft.'; }
    ready = true;
    api('/config').then(value => { if (active) config = value; }).catch(() => error = 'The API is unavailable. Your local editing tools still work.');
    api('/templates').then(value => { if (active) templates = value; }).catch(() => {});
    refreshUser().then(async () => {
      const project = restoredProject;
      if (!user || !project || !active) return;
      try {
        const fresh = await api(`/projects/${project.id}`);
        if (!active || restoredProject?.id !== project.id) return;
        current = { ...fresh, version: project.version };
        saved = project.saved;
        restoredProject = null;
        applicationId = fresh.application_id || '';
        guildId = fresh.guild_id || '';
      } catch { if (active) { restoredProject = null; notice = 'The saved project is unavailable. Your local draft is safe; save it as a new project.'; } }
    });
    const interval = setInterval(() => { if (current && user) refreshStatus(); }, 8000);
    return () => { active = false; clearInterval(interval); };
  });
  function commit(next: Definition) {
    undoStack = [...undoStack.slice(-49), clone(definition)]; redoStack = []; definition = next; preview = null; syncDiff = null; simulationState = {values:{},jobs:{}}; localSaved = false;
  }
  function patch(patch: Record<string, unknown>) {
    const next = clone(definition);
    next.nodes = next.nodes.map(node=>node.id===selectedId?{...node,...patch} as Block:node);
    if (patch.operation==='moderation') {
      const removed=next.edges.filter(edge=>edge.source===selectedId);
      next.edges=next.edges.filter(edge=>edge.source!==selectedId);
      for(const edge of removed) {
        if(!next.edges.some(e=>e.target===edge.target || e.source===edge.target)) {
          next.nodes=next.nodes.filter(node=>node.id!==edge.target);
          delete next.layout.positions[edge.target];
        }
      }
    }
    commit(next);
  }
  function undo() { const previous = undoStack.at(-1); if (previous) { redoStack = [...redoStack, clone(definition)]; undoStack = undoStack.slice(0, -1); definition = previous; preview = null; } }
  function redo() { const next = redoStack.at(-1); if (next) { undoStack = [...undoStack, clone(definition)]; redoStack = redoStack.slice(0, -1); definition = next; preview = null; } }
  function useTemplate(name: string) {
    if (dirty && !confirm('Replace this draft with a template? Export or save first to keep it.')) return;
    commit(clone(templates[name])); current = null; restoredProject = null; saved = ''; selectedId = definition.nodes[0].id; previewCommand = selectedId; notice = 'Template loaded.';
  }
  function connect(connection: Connection) {
    if (!connection.source || !connection.target || connection.source === connection.target) return;
    const branch = (connection.sourceHandle || 'next') as 'next' | 'true' | 'false';
    commit({ ...definition, edges: [...definition.edges.filter(edge => !(edge.source === connection.source && (edge.branch || 'next') === branch)), { id: crypto.randomUUID(), source: connection.source, target: connection.target, branch }] });
  }
  function connectList(source: string, branch: 'next' | 'true' | 'false', target: string) {
    if (!target) { commit({ ...definition, edges: definition.edges.filter(edge => !(edge.source === source && (edge.branch || 'next') === branch)) }); return; }
    connect({ source, target, sourceHandle: branch, targetHandle: null });
  }
  function add(kind: Block['kind'], position?: { x: number; y: number }) {
    const id = crypto.randomUUID();
    const base: Block = kind === 'message' ? {id,kind,content:'Choose an action',buttons:[{label:'Click me',reply:'Hello!',url:null}],selects:[],attachments:[],owner_only:true,timeout:180,ephemeral:false} : kind === 'form' ? {id,kind,title:'Feedback',inputs:[{name:'feedback',label:'Your feedback',required:true,max_length:1000,paragraph:true}],response:'Thanks for your feedback!'} : kind === 'action' ? {id,kind,operation:'store_increment',key:'visits',value:'1',target:'{{user.id}}',response:'Value: {{store.value}}',ephemeral:true} : kind === 'trigger' ? { id, kind, name: `command${triggers.length + 1}`, mode: 'slash', description: 'A new command', cooldown: 0 } : kind === 'condition' ? { id, kind, field: 'role', value: '123456789' } : kind === 'embed' ? { id, kind, title: 'New embed', description: 'Made for {{user.display_name}}.', color: '#ff7a30', image_url: null, ephemeral: false } : { id, kind, content: 'Hello, {{user.display_name}}!', ephemeral: false };
    const next = clone(definition);
    next.nodes.push(base);
    const start = next.layout.positions[selectedId] || { x: 80, y: 100 };
    next.layout.positions[id] = { x: start.x + 320, y: start.y };
    if (kind === 'trigger') {
      const reply = crypto.randomUUID();
      next.nodes.push({ id: reply, kind: 'reply', content: 'Hello, {{user.display_name}}!', ephemeral: false });
      next.edges.push({ id: crypto.randomUUID(), source: id, target: reply, branch: 'next' });
      next.layout.positions[reply] = { x: start.x + 640, y: start.y + 180 };
    } else {
      const source = next.nodes.find(node => node.id === selectedId);
      const branch = source?.kind === 'condition' ? 'true' : 'next';
      const old = next.edges.find(edge => edge.source === selectedId && (edge.branch || 'next') === branch);
      if (source) {
        next.edges = next.edges.filter(edge => edge.id !== old?.id);
        next.edges.push({ id: crypto.randomUUID(), source: selectedId, target: id, branch });
      }
      if (kind === 'condition') {
        for (const [index, branch] of (['true', 'false'] as const).entries()) {
          const reply = branch === 'true' && old ? old.target : crypto.randomUUID();
          if (!(branch === 'true' && old)) {
            next.nodes.push({ id: reply, kind: 'reply', content: branch === 'true' ? 'You’re in the right place.' : 'This command is not available here.', ephemeral: false });
            next.layout.positions[reply] = { x: start.x + 640, y: start.y + index * 200 };
          }
          next.edges.push({ id: crypto.randomUUID(), source: id, target: reply, branch });
        }
      } else if (old && kind !== 'form') next.edges.push({ ...old, id: crypto.randomUUID(), source: id, branch: 'next' });
      if (kind === 'form' && old) {
        const oldTarget = next.nodes.find(n=>n.id===old.target);
        if (oldTarget && !next.edges.some(e=>e.target===old.target) && !next.edges.some(e=>e.source===old.target)) {
          next.nodes = next.nodes.filter(n=>n.id!==old.target); delete next.layout.positions[old.target];
        }
      }
    }
    if (position) {
      const origin = next.layout.positions[id];
      for (const node of next.nodes.filter(node => !definition.nodes.some(old => old.id === node.id))) {
        const point = next.layout.positions[node.id];
        next.layout.positions[node.id] = { x: point.x + position.x - origin.x, y: point.y + position.y - origin.y };
      }
    }
    commit(next); selectedId = id;
  }
  function removeBlock() {
    if (!selected) return;
    const next = clone(definition);
    next.nodes = next.nodes.filter(node => node.id !== selectedId);
    next.edges = next.edges.filter(edge => edge.source !== selectedId && edge.target !== selectedId);
    delete next.layout.positions[selectedId];
    commit(next); selectedId = next.nodes[0]?.id || '';
  }
  async function task(action: () => Promise<void>) { if (busy || !ready) return; busy = true; error = ''; notice = ''; try { await action(); } catch (cause) { error = cause instanceof Error ? cause.message : 'Something went wrong. Try again.'; } finally { busy = false; } }
  async function refreshUser() {
    try { const result = await api('/auth/me'); user = result; setCsrf(result.csrf); projects = await api('/projects'); }
    catch { user = null; setCsrf(''); }
  }
  async function refreshStatus() {
    if (!current) return;
    try { const fresh = await api(`/projects/${current.id}`); if (current?.id === fresh.id) current = { ...current, ...fresh, definition: current.definition, version: current.version }; events = await api(`/projects/${fresh.id}/events`); revisions = await api(`/projects/${fresh.id}/revisions`); } catch { /* Keep local draft when offline. */ }
  }
  async function openProject(id: string) {
    if (!id) return;
    if (dirty && !confirm('Open this project and replace the current draft?')) return;
    await task(async () => { current = await api(`/projects/${id}`); definition = clone(current!.definition); saved = JSON.stringify(definition); undoStack = []; redoStack = []; selectedId = definition.nodes[0].id; previewCommand = selectedId; applicationId = current!.application_id || ''; guildId = current!.guild_id || ''; await refreshStatus(); });
  }
  async function saveProject() {
    if (restoredProject) throw new Error('Your saved project is still loading. Try saving again in a moment.');
    if (!user) throw new Error('Sign in to save across devices. Your draft is also stored in this browser.');
    const snapshot = clone(definition);
    current = current ? await api(`/projects/${current.id}`, 'PUT', { definition: snapshot, version: current.version }) : await api('/projects', 'POST', snapshot);
    saved = JSON.stringify(snapshot); projects = await api('/projects'); notice = 'Project saved.';
  }
  async function runPreview(component?: Record<string,unknown>) {
    const trigger = triggers.find(node => node.id === previewCommand) || triggers[0];
    if (!trigger || trigger.kind !== 'trigger') throw new Error('Add a command trigger first.');
    const options:Record<string,string|number|boolean> = {};
    for (const option of trigger.options || []) {
      const value = previewOptions[option.name];
      if ((value===undefined || value==='') && !option.required) continue;
      options[option.name] = option.type==='bool'?value==='true':option.type==='int'||option.type==='float'?Number(value):value || '';
    }
    preview = await api('/preview', 'POST', { definition, command: trigger.name, mode: trigger.mode==='both'?previewMode:trigger.mode || 'slash', options, component, state:simulationState, context: { display_name: previewName, user_name: previewName, server_name: previewServer, channel_name: previewChannel, channel_id: previewChannelId, role_ids: previewRoles.split(',').map(value => value.trim()).filter(Boolean), permissions:previewPermissions.split(',').map(v=>v.trim()).filter(Boolean), age_restricted:previewAgeRestricted, in_server:previewInServer } });
    simulationState = preview!.state;
  }
  async function clickComponent(message:PreviewMessage,type:string,index=0,value='') {
    await runPreview({node_id:message.node_id,type,index,value,inputs:modalValues});
  }
  async function previewHook() {
    preview = await api('/preview-hook','POST',{definition,index:Number(hookIndex),match:hookMatch,context:{display_name:previewName,user_name:previewName,channel_id:previewChannelId,channel_name:previewChannel,server_name:previewServer,in_server:previewInServer}});
  }
  async function syncPreview() {
    let remote:unknown;
    try { remote=JSON.parse(syncSnapshot); } catch { throw new Error('Paste a valid JSON array of registered commands.'); }
    if (!Array.isArray(remote)) throw new Error('Registered commands must be a JSON array.');
    syncDiff = await api('/sync-preview','POST',{definition,remote,guild_id:guildId || null});
  }
  async function exportBot() {
    const response = await fetch('/api/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(definition) });
    if (!response.ok) { const result = await response.json(); throw new Error(Array.isArray(result.detail) ? result.detail.map((item: {msg: string}) => item.msg).join('\n') : result.detail); }
    const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'discord-bot.zip'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); notice = 'Exported. Your bot is ready to run with Python.';
  }
  async function importBot(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]; if (!file) return;
    await task(async () => { if (file.size > 262144) throw new Error('Choose a bot.json file smaller than 256 KiB.'); const result = await api('/validate', 'POST', JSON.parse(await file.text())); if (dirty && !confirm('Replace your current draft with this imported bot?')) return; commit(result.definition); current = null; restoredProject = null; saved = ''; selectedId = definition.nodes[0].id; previewCommand = selectedId; notice = 'Definition imported.'; }); fileInput.value = '';
  }
  async function deleteProject() {
    if (!current || !confirm('Delete this saved project and its published versions?')) return;
    await api(`/projects/${current.id}`, 'DELETE');
    current = null; restoredProject = null; projects = await api('/projects');
    notice = 'Project deleted. Local draft kept.';
  }
  async function publish() {
    if (!user?.can_host) { error = 'Hosted publishing is limited to the owner pilot. Export your bot to run it yourself.'; return; }
    await saveProject();
    if (!current?.has_token) { credentials = true; return; }
    await api(`/projects/${current.id}/publish`, 'POST', { version: current.version }); await refreshStatus(); notice = 'Published. The runner will connect shortly.';
  }
  async function saveCredentials() {
    if (!current) await saveProject();
    await api(`/projects/${current!.id}/credentials`, 'PUT', { token, application_id: applicationId, guild_id: guildId || null }); token = ''; credentials = false; await refreshStatus(); notice = 'Credentials saved securely. Publish when ready.';
  }
  function keyboard(event: KeyboardEvent) {
    if ((event.metaKey || event.ctrlKey) && event.key === 's') { event.preventDefault(); task(saveProject); }
    const input = event.target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName);
    if (!input && (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); event.shiftKey ? redo() : undo(); }
  }
</script>
<svelte:window onkeydown={keyboard}/>
<svelte:head><title>Visual builder — Discord Bot Maker</title><meta name="description" content="Connect blocks, preview replies, and export your Discord bot."/></svelte:head>
<main id="main" class="builder-shell" aria-busy={!ready}>
  <fieldset class="editor-readiness" disabled={!ready}>
  <div class="workspace-heading"><div><h1>Builder</h1></div><div class="account">{#if user}<span>{user.name}</span><button class="icon-button" aria-label="Sign out" onclick={() => task(async () => { await api('/auth/logout', 'POST'); user = null; setCsrf(''); projects = []; current = null; restoredProject = null; })}><LogOut size={16}/></button>{:else}{#if config.oauth_enabled}<a class="button secondary" href="/api/auth/login">Sign in with Discord <ArrowRight size={14}/></a>{/if}{#if config.dev_login}<button class="button secondary" onclick={() => task(async () => { await fetch('/api/auth/dev', { method: 'POST' }); await refreshUser(); })}>Local sign in</button>{/if}{/if}</div></div>
  <section class="workshop glass" aria-label="Bot editor">
    <div class="workshop-toolbar"><div class="project-title"><span class="project-icon"><Workflow size={19}/></span><div><input aria-label="Bot name" maxlength="80" value={definition.name} onchange={event => commit({ ...definition, name: event.currentTarget.value })}/><small><span class="status-dot"></span>{current && !dirty ? 'Saved' : localSaved ? 'Saved locally' : 'Saving…'}</small></div></div><div class="toolbar-actions">{#if user || config.oauth_enabled || config.dev_login}<button class="button secondary compact" disabled={busy || !ready} onclick={() => task(saveProject)}><Save size={15}/><span>Save</span></button>{/if}<button class="button secondary compact" disabled={busy || !ready} onclick={() => task(exportBot)}><Download size={15}/><span>Export</span></button>{#if user?.can_host}<button class="button primary compact" disabled={busy || !ready} onclick={() => task(publish)}><Cloud size={15}/> Publish</button>{/if}</div></div>
    <div class="editor-grid">
      <aside class="palette"><h2>Blocks</h2><div class="palette-buttons">{#each [{kind:'trigger', icon:Hash, title:'Command'}, {kind:'reply', icon:MessageSquare, title:'Reply'}, {kind:'embed', icon:PanelTop, title:'Embed'}, {kind:'condition', icon:GitBranch, title:'Condition'}, {kind:'message', icon:MessageSquare, title:'Interactive'}, {kind:'form', icon:PanelTop, title:'Form'}, {kind:'action', icon:Workflow, title:'Action'}] as item}<button class="palette-block" draggable="true" ondragstart={event => { event.dataTransfer?.setData('application/dbm-block', item.kind); if (event.dataTransfer) event.dataTransfer.effectAllowed = 'copy'; }} onclick={() => add(item.kind as Block['kind'])}><span class="palette-icon"><item.icon size={18}/></span><span><strong>{item.title}</strong></span></button>{/each}</div><div class="palette-divider"></div><label class="field-label" for="templates">Templates</label><select id="templates" value="" onchange={event => { if (event.currentTarget.value) useTemplate(event.currentTarget.value); event.currentTarget.value = ''; }}><option value="">Choose a template</option>{#each Object.entries(templates) as [key, item]}<option value={key}>{item.name}</option>{/each}</select><button class="text-button" onclick={() => fileInput.click()}><Upload size={14}/> Import bot.json</button><input class="visually-hidden" bind:this={fileInput} type="file" accept=".json,application/json" onchange={importBot}/>{#if user}<label class="field-label" for="projects">Projects</label><select id="projects" value={current?.id || ''} onchange={event => openProject(event.currentTarget.value)}><option value="">Choose a project</option>{#each projects as project}<option value={project.id}>{project.name}</option>{/each}</select><button class="text-button" onclick={() => { current = null; restoredProject = null; saved = ''; notice = 'The next save will create a new project.'; }}><Plus size={14}/> Duplicate project</button>{#if current && !user.can_host}<button class="text-button danger" onclick={() => task(deleteProject)}>Delete project</button>{/if}{/if}</aside>
      <section class="canvas-section" aria-label="Flow canvas"><div class="canvas-toolbar"><div class="segmented"><button class:active={!listView} onclick={() => listView = false}><Workflow size={14}/> Canvas</button><button class:active={listView} onclick={() => listView = true}><List size={14}/> List</button></div><div class="history-controls"><button class="icon-button" aria-label="Undo" disabled={!undoStack.length} onclick={undo}><Undo2 size={15}/></button><button class="icon-button" aria-label="Redo" disabled={!redoStack.length} onclick={redo}><Redo2 size={15}/></button></div></div>
      <div class="canvas-area">{#if listView}<div class="flow-list">{#each definition.nodes as node}<button class:active={selectedId === node.id} onclick={() => selectedId = node.id}><span class="panel-eyebrow">{node.kind}</span><strong>{label(node)}</strong><small>{summary(node)}</small></button>{/each}</div>{:else}<SvelteFlow bind:nodes={flowNodes} bind:edges={flowEdges} {nodeTypes} fitView minZoom={0.25} maxZoom={1.5} colorMode="dark" onnodeclick={({node}) => selectedId = node.id} onconnect={connect} onnodedragstop={({nodes}) => { const next = clone(definition); for (const node of nodes) next.layout.positions[node.id] = node.position; commit(next); }} ondelete={({nodes, edges}) => { const ids = new Set(nodes.map(node => node.id)); const next = clone(definition); next.nodes = next.nodes.filter(node => !ids.has(node.id)); next.edges = next.edges.filter(edge => !ids.has(edge.source) && !ids.has(edge.target) && !edges.some(item => item.id === edge.id)); for (const id of ids) delete next.layout.positions[id]; commit(next); }}><CanvasDrop onadd={add}/><Background gap={22} patternColor="#6b625633"/><Controls showLock={false}/><MiniMap width={128} height={88} pannable zoomable ariaLabel="Flow overview" nodeColor="#ff7a30" maskColor="var(--line)" maskStrokeColor="var(--muted)" maskStrokeWidth={1}/></SvelteFlow>{/if}</div><div class="canvas-status">{#if validation}<CircleHelp size={14}/><span>{validation}</span>{:else}<Check size={14}/><span>Valid flow</span>{/if}<span class="node-count">{definition.nodes.length} blocks</span></div></section>
      <aside class="inspector"><div class="inspector-title"><span class="panel-eyebrow">Settings</span>{#if selected}<button class="icon-button danger" aria-label="Delete selected block" onclick={removeBlock}><Trash2 size={14}/></button>{/if}</div>{#if selected}<h2>{label(selected)}</h2><div class="settings-fields">{#if selected.kind === 'trigger'}<label>Command name<input value={selected.name} maxlength="32" oninput={event => patch({ name: event.currentTarget.value })}/></label><label>Description<input value={selected.description || ''} maxlength="100" oninput={event => patch({ description: event.currentTarget.value })}/></label><div class="field-row"><label>Trigger type<select value={selected.mode || 'slash'} onchange={event => patch({ mode: event.currentTarget.value })}><option value="slash">Slash /</option><option value="prefix">Prefix</option><option value="both">Slash + prefix</option></select></label><label>Cooldown (sec)<input type="number" min="0" max="86400" value={selected.cooldown || 0} onchange={event => patch({ cooldown: +event.currentTarget.value })}/></label></div>{#if selected.mode === 'prefix' || selected.mode === 'both'}<label>Bot prefix<input value={definition.prefix} maxlength="10" onchange={event => commit({ ...definition, prefix: event.currentTarget.value })}/></label><p class="micro">Enable Message Content Intent in Discord.</p>{/if}{:else if selected.kind === 'reply'}<label>Reply message<textarea rows="5" maxlength="2000" value={selected.content} oninput={event => patch({ content: event.currentTarget.value })}></textarea></label>{:else if selected.kind === 'embed'}<label>Title<input value={selected.title} maxlength="256" oninput={event => patch({ title: event.currentTarget.value })}/></label><label>Description<textarea rows="4" maxlength="4096" value={selected.description} oninput={event => patch({ description: event.currentTarget.value })}></textarea></label><label>Accent color<input type="color" value={selected.color} oninput={event => patch({ color: event.currentTarget.value })}/></label><label>Image URL<input type="url" placeholder="https://…" value={selected.image_url || ''} onchange={event => patch({ image_url: event.currentTarget.value || null })}/></label>{:else if selected.kind === 'condition'}<label>Check whether the user<select value={selected.field} onchange={event => patch({ field: event.currentTarget.value })}><option value="role">Has a role</option><option value="channel">Is in a channel</option></select></label><label>{selected.field === 'role' ? 'Role ID' : 'Channel ID'}<input value={selected.value} oninput={event => patch({ value: event.currentTarget.value })}/></label><p class="micro">Enable Developer Mode in Discord to copy IDs.</p>{/if}<AdvancedFields {selected} {patch}/>{#if selected.kind === 'reply' || selected.kind === 'embed' || selected.kind === 'message' || selected.kind === 'action'}<label class="checkbox-label"><input type="checkbox" checked={selected.ephemeral} onchange={event => patch({ ephemeral: event.currentTarget.checked })}/> Private reply (slash only)</label><details class="variables"><summary>Variables</summary><div class="variable-list">{#each config.variables as variable}<button onclick={() => { if (!selected) return; const field = selected.kind === 'reply' || selected.kind === 'message' ? 'content' : selected.kind === 'action' ? 'response' : 'description'; const value = field in selected ? String(selected[field as keyof typeof selected] || '') : ''; patch({ [field]: `${value} {{${variable}}}` }); }}>{'{{' + variable + '}}'}</button>{/each}</div></details>{/if}<div class="connections"><span class="field-label">Connections</span>{#each (selected.kind === 'condition' ? ['true', 'false'] : ['next']) as branch}<label>{branch === 'next' ? 'Next step' : branch === 'true' ? 'If true' : 'If false'}<select value={definition.edges.find(edge => edge.source === selectedId && (edge.branch || 'next') === branch)?.target || ''} onchange={event => connectList(selectedId, branch as 'next' | 'true' | 'false', event.currentTarget.value)}><option value="">End of flow</option>{#each definition.nodes.filter(node => node.id !== selectedId && node.kind !== 'trigger') as target}<option value={target.id}>{label(target)} · {target.id.slice(0, 6)}</option>{/each}</select></label>{/each}</div></div>{:else}<p class="micro">Select a block to edit.</p>{/if}</aside>
    </div>
  </section>
  <BotSettings runtime={definition.runtime || defaultRuntime} prefix={definition.prefix} onchange={runtime=>commit({...definition,runtime})} onprefix={prefix=>commit({...definition,prefix})}/>
  {#if error}<div class="feedback error" role="alert"><CircleHelp size={17}/><span>{error}</span><button class="icon-button" aria-label="Dismiss error" onclick={() => error = ''}><X size={14}/></button></div>{/if}{#if notice}<div class="feedback success" role="status"><Check size={17}/>{notice}</div>{/if}
  <section class="preview-panel glass"><div class="preview-settings"><h2>Test bot</h2><div class="preview-command"><select aria-label="Command to preview" bind:value={previewCommand}>{#each triggers as trigger}<option value={trigger.id}>{label(trigger)}</option>{/each}</select><button class="button primary" disabled={busy || !ready || !triggers.length} onclick={() => task(runPreview)}><Play size={14}/> Preview</button></div><div class="context-fields">
    {#if triggers.find(t=>t.id===previewCommand)?.mode==='both'}<label>Simulation mode<select bind:value={previewMode}><option value="slash">Slash</option><option value="prefix">Prefix</option></select></label>{/if}
    {#each triggers.find(t=>t.id===previewCommand)?.options || [] as option}<label>Argument: {option.name}{#if option.type==='bool'}<select bind:value={previewOptions[option.name]}><option value="false">false</option><option value="true">true</option></select>{:else}<input type="text" list={`suggest-${option.name}`} placeholder={String(option.default ?? '')} bind:value={previewOptions[option.name]}/><datalist id={`suggest-${option.name}`}>{#each option.choices?.length?option.choices:option.autocomplete || [] as choice}<option value={choice}></option>{/each}</datalist>{/if}</label>{/each}
    </div><button class="text-button" onclick={() => {simulationState={values:{},jobs:{}};preview=null;notice='Simulation reset.';}}>Reset simulation</button>
    {#if definition.runtime?.hooks?.length}<details><summary>Simulate an event hook</summary><label>Hook to test<select bind:value={hookIndex}>{#each definition.runtime.hooks as hook,index}<option value={String(index)}>{hook.event}: {hook.match}</option>{/each}</select></label><label>Event message or emoji<input bind:value={hookMatch}/></label><button class="button secondary compact" onclick={()=>task(previewHook)}>Simulate event</button></details>{/if}
    <button class="text-button" onclick={() => showContext = !showContext}>{showContext ? 'Hide' : 'Edit'} sample context</button>{#if showContext}<div class="context-fields"><label>User name<input bind:value={previewName}/></label><label>Server name<input bind:value={previewServer}/></label><label>Channel name<input bind:value={previewChannel}/></label><label>Channel ID<input bind:value={previewChannelId}/></label><label>Role IDs (comma separated)<input bind:value={previewRoles}/></label><label>Permissions (comma separated)<input bind:value={previewPermissions} placeholder="manage_guild, kick_members"/></label><label class="checkbox-label"><input type="checkbox" bind:checked={previewAgeRestricted}/> Age-restricted channel</label><label class="checkbox-label"><input type="checkbox" bind:checked={previewInServer}/> In a server</label></div>{/if}</div><div class="preview-output">{#if preview}<div class="discord-message"><div class="bot-avatar"><Sparkles size={20}/></div><div class="messages"><div class="message-author">{definition.name}<span class="bot-badge">APP</span><small> Just now · preview</small></div>{#each preview.messages as message}{#if message.kind === 'reply'}<p>{message.content}</p>
    {:else if message.kind === 'embed'}<div class="embed-preview" style:border-left-color={message.color}><strong>{message.title}</strong><p>{message.description}</p>{#each message.fields || [] as field}<div><strong>{field.name}</strong><p>{field.value}</p></div>{/each}{#if message.footer}<small>{message.footer}</small>{/if}{#if message.image_url}<a href={message.image_url} target="_blank" rel="noreferrer">Attached image ↗</a>{/if}</div>
    {:else if message.kind === 'message'}<p>{message.content}</p><div class="component-preview">{#each message.buttons || [] as button,index}{#if button.url}<a class="button secondary compact" href={button.url} target="_blank" rel="noreferrer">{button.label} ↗</a>{:else}<button class="button secondary compact" onclick={()=>task(()=>clickComponent(message,'button',index))}>{button.label}</button>{/if}{/each}{#each message.selects || [] as select,index}<select aria-label={select.placeholder} value="" onchange={e=>task(()=>clickComponent(message,'select',index,e.currentTarget.value))}><option value="">{select.placeholder}</option>{#each select.options as option}<option>{option}</option>{/each}</select>{/each}</div>{#each message.attachments || [] as file}<details><summary>📎 {file.filename}</summary><pre>{file.content}</pre></details>{/each}
    {:else if message.kind==='form'}<form class="simulated-modal" onsubmit={e=>{e.preventDefault();task(()=>clickComponent(message,'form'));}}><h3>{message.title}</h3>{#each message.inputs || [] as input}<label>{input.label}<textarea rows={input.paragraph?3:1} required={input.required} maxlength={input.max_length} bind:value={modalValues[input.name]}></textarea></label>{/each}<button class="button primary compact">Submit form</button></form>
    {:else}<div class="action-preview"><p>{message.content}</p>{#if message.operation==='moderation'}<p class="micro">Simulation only. Live execution requires confirmation and checks bot/caller permissions and role hierarchy.</p>{/if}</div>{/if}{#if message.ephemeral}<small class="micro">Only visible to you</small>{/if}{/each}</div></div><details class="trace"><summary>{preview.trace.length} steps · View execution trace</summary>{#each preview.trace as step}<p><Check size={12}/>{definition.nodes.find(node => node.id === step.id)?.kind} {step.result ? `→ ${step.result}` : ''}</p>{/each}</details>{:else}<div class="empty-preview"><p>Run a command to preview its reply.</p></div>{/if}</div></section>
  <section class="bot-settings glass"><details><summary>Command registration preview</summary><p class="micro">Paste a saved Discord registration snapshot to compare it with this bot. An empty array shows a first registration. This tool never connects to Discord or synchronizes commands.</p><label>Registered commands JSON<textarea rows="4" bind:value={syncSnapshot}></textarea></label><label>Registration server ID (empty for global)<input inputmode="numeric" bind:value={guildId}/></label><button class="button secondary compact" disabled={busy} onclick={()=>task(syncPreview)}>Compare registration</button>{#if syncDiff}<p>Scope: {syncDiff.scope}</p>{#each syncDiff.changes as change}<details class="registration-change"><summary>{change.action}: {change.name}</summary><h4>Before</h4><pre>{JSON.stringify(change.before,null,2)}</pre><h4>After</h4><pre>{JSON.stringify(change.after,null,2)}</pre></details>{/each}{/if}</details></section>
  {#if current && user?.can_host}<section class="hosting-panel glass"><div><h2>{current.name}</h2>{#if user?.can_host}<p>Status: <strong>{current.observed_state}</strong> · {current.published_revision ? 'Published' : 'Unpublished'}</p>{/if}<div class="hosting-actions">{#if user?.can_host}<button class="button secondary" onclick={() => { applicationId = current?.application_id || ''; guildId = current?.guild_id || ''; credentials = !credentials; }}> {current.has_token ? 'Rotate credentials' : 'Connect bot'}</button><button class="button secondary" onclick={() => task(async () => { await api(`/projects/${current!.id}/stop`, 'POST'); await refreshStatus(); })}>Stop bot</button>{#if current.has_token}<button class="text-button" onclick={() => task(async () => { if (!confirm('Remove stored bot credentials and stop the hosted bot?')) return; await api(`/projects/${current!.id}/credentials`, 'DELETE'); await refreshStatus(); })}>Remove credentials</button>{/if}{/if}<button class="text-button danger" onclick={() => task(deleteProject)}>Delete project</button></div>{#if current.application_id}<a class="text-button" target="_blank" rel="noreferrer" href={`https://discord.com/oauth2/authorize?client_id=${current.application_id}&scope=bot%20applications.commands&permissions=19456`}>Invite bot to your server ↗</a>{/if}</div>{#if credentials}<form class="credential-form" onsubmit={event => { event.preventDefault(); task(saveCredentials); }}><p>Create your bot in the Discord Developer Portal. Your token is encrypted and is never included in exports.</p><label>Application ID<input required inputmode="numeric" bind:value={applicationId}/></label><label>Test server ID (optional)<input inputmode="numeric" bind:value={guildId}/></label><label>Bot token<input required type="password" autocomplete="new-password" bind:value={token}/></label><button class="button primary" disabled={busy || !ready}>Save credentials</button></form>{/if}{#if revisions.length}<details><summary>Published versions</summary>{#each revisions as revision}<div class="revision-row"><span>{new Date(revision.created_at * 1000).toLocaleString()}</span><button disabled={revision.id === current.published_revision || busy} class="text-button" onclick={() => task(async () => { await api(`/projects/${current!.id}/rollback`, 'POST', { revision_id: revision.id }); await refreshStatus(); notice = 'Selected the earlier published version.'; })}> {revision.id === current.published_revision ? 'Active version' : 'Rollback'}</button></div>{/each}</details>{/if}{#if events.length}<details><summary>Runner activity</summary>{#each events as event}<p class="micro">{new Date(event.created_at * 1000).toLocaleTimeString()} · {event.message}</p>{/each}</details>{/if}</section>{/if}

</fieldset>
</main>
