<script lang="ts">
  import { Handle, Position, type NodeProps } from '@xyflow/svelte';
  import { Hash, MessageSquare, GitBranch, PanelTop } from '@lucide/svelte';
  let { data, selected }: NodeProps = $props();
  const icons = { trigger: Hash, reply: MessageSquare, condition: GitBranch, embed: PanelTop };
  let kind = $derived(String(data.kind));
  let Icon = $derived(icons[kind as keyof typeof icons] || MessageSquare);
</script>
<div class:selected class="flow-block" class:condition={kind === 'condition'}>
  {#if kind !== 'trigger'}<Handle type="target" position={Position.Left}/>{/if}
  <div class="block-caption"><Icon size={15}/><span>{kind === 'trigger' ? 'Command' : kind.charAt(0).toUpperCase() + kind.slice(1)}</span></div>
  <strong>{String(data.label || kind)}</strong>
  <p>{String(data.summary || '')}</p>
  {#if kind === 'condition'}
    <div class="branch-labels"><span>True</span><span>False</span></div>
    <Handle id="true" type="source" position={Position.Right} style="top: 35%; background: #b7c5a4"/>
    <Handle id="false" type="source" position={Position.Right} style="top: 75%; background: #e49b89"/>
  {:else}<Handle id="next" type="source" position={Position.Right}/>{/if}
</div>
