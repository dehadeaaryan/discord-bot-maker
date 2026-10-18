<script lang="ts">
  import { useSvelteFlow } from '@xyflow/svelte';
  import type { Block } from '../model';
  let { onadd }: { onadd: (kind: Block['kind'], position: {x: number; y: number}) => void } = $props();
  const { screenToFlowPosition } = useSvelteFlow();
  function drop(event: DragEvent) {
    if (!(event.target instanceof Element) || !event.target.closest('.svelte-flow')) return;
    event.preventDefault();
    const kind = event.dataTransfer?.getData('application/dbm-block');
    if (kind === 'trigger' || kind === 'reply' || kind === 'embed' || kind === 'condition' || kind === 'message' || kind === 'form' || kind === 'action') {
      onadd(kind, screenToFlowPosition({ x: event.clientX, y: event.clientY }));
    }
  }
</script>
<svelte:window ondrop={drop} ondragover={event => {
  if (event.dataTransfer?.types.includes('application/dbm-block')) {
    event.preventDefault(); event.dataTransfer.dropEffect = 'copy';
  }
}}/>
