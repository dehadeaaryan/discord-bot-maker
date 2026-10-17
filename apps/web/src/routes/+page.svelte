<script lang="ts">
  import { ArrowRight, Code, Sparkles, MessageSquare, Hash } from '@lucide/svelte';
</script>

<svelte:head>
  <title>Discord Bot Maker — Build your bot</title>
  <meta name="description" content="Build a Discord bot with blocks. Preview it, then export it to Python."/>
</svelte:head>

<main id="main" class="landing">
  <section class="hero">
    <div class="hero-copy">
      <h1>Build your<br/><em>Discord bot.</em></h1>
      <p class="hero-description">Connect blocks. Preview replies. Export to Python.</p>
      <div class="hero-actions">
        <a class="button primary" href="/builder">Build a bot <ArrowRight size={17}/></a>
        <a class="quiet-link" href="/help#python">Python library <Code size={16}/></a>
      </div>
    </div>
    <div class="hero-workspace" aria-label="Example command and reply">
      <div class="preview-top"><span><span class="status-dot"></span> /hello</span><span>PREVIEW</span></div>
      <div class="demo-flow">
        <div class="demo-node"><div class="block-caption"><Hash size={15}/> COMMAND</div><strong>/hello</strong></div>
        <div class="demo-connector"><span></span><ArrowRight size={19}/></div>
        <div class="demo-node reply-demo"><div class="block-caption"><MessageSquare size={15}/> REPLY</div><strong>Hello, {'{{user.display_name}}'}!</strong></div>
      </div>
      <div class="discord-message">
        <div class="bot-avatar"><Sparkles size={22}/></div>
        <div><div class="message-author">Your bot <span class="bot-badge">APP</span></div><p>Hello, Aaryan! 👋</p></div>
      </div>
    </div>
  </section>
  <footer><a href="https://apps.aaryandehade.com">By Aaryan ↗</a><a href="/help">Guide</a></footer>
</main>
