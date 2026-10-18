<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { Sun, Moon, ArrowUpRight } from '@lucide/svelte';
  let { children, data } = $props();
  let light = $state(false);
  onMount(() => { light = localStorage.getItem('dbm-theme') === 'light'; document.documentElement.classList.toggle('light', light); });
  function toggle() { light = !light; localStorage.setItem('dbm-theme', light ? 'light' : 'dark'); document.documentElement.classList.toggle('light', light); }
</script>
<svelte:head>
  <meta name="theme-color" content="#171514" />
  <link rel="canonical" href={data.pageUrl}/>
  <meta property="og:type" content="website"/>
  <meta property="og:site_name" content="Discord Bot Maker"/>
  <meta property="og:title" content="Discord Bot Maker"/>
  <meta property="og:description" content="Build a Discord bot with blocks. Preview replies. Export to Python."/>
  <meta property="og:url" content={data.pageUrl}/>
  <meta property="og:image" content={`${data.siteOrigin}/social-preview.png`}/>
  <meta property="og:image:type" content="image/png"/>
  <meta property="og:image:width" content="1200"/>
  <meta property="og:image:height" content="630"/>
  <meta property="og:image:alt" content="Discord Bot Maker landing page with a command connected to a reply."/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="Discord Bot Maker"/>
  <meta name="twitter:description" content="Build a Discord bot with blocks. Preview replies. Export to Python."/>
  <meta name="twitter:image" content={`${data.siteOrigin}/social-preview.png`}/>
  <meta name="twitter:image:alt" content="Discord Bot Maker landing page with a command connected to a reply."/>
</svelte:head>
<a class="skip-link" href="#main">Skip to content</a>
<div class="ambient" aria-hidden="true"></div>
<header class="site-header">
  <a class="brand-link" href="/">
    <img src="/ad-logo.png?v=cyan-glitch-1" width="46" height="32" alt=""/>
    <span>Discord Bot Maker<span class="accent-dot">.</span></span>
  </a>
  <nav class="site-nav" aria-label="Main navigation">
    <a class="header-button" href="/help">Guide</a>
    <a class="header-button desktop-link" href="https://github.com/dehadeaaryan/discord-bot-maker">GitHub <ArrowUpRight size={13}/></a>
    <button class="header-button theme-toggle" onclick={toggle} aria-label={light ? 'Switch to dark theme' : 'Switch to light theme'}>
      {#if light}<Moon size={17}/>{:else}<Sun size={17}/>{/if}
    </button>
  </nav>
</header>
{@render children()}

<style>
  .site-header {
    position: relative;
    z-index: 10;
    width: calc(100% - 48px);
    max-width: 1176px;
    margin: 16px auto 0;
    min-height: 76px;
    padding: 12px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    border: 1px solid var(--line);
    border-radius: 99px;
    background: #ffffff0d;
    backdrop-filter: blur(24px) saturate(1.5);
    box-shadow: inset 0 1px #ffffff20, 0 8px 30px #0003;
  }
  .brand-link {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -.05em;
    white-space: nowrap;
  }
  .brand-link img {
    width: 46px;
    height: 32px;
    object-fit: contain;
    filter: drop-shadow(0 0 8px #00eaff40);
    transition: transform .2s, filter .2s;
  }
  .brand-link:hover img, .brand-link:focus-visible img {
    transform: rotate(-3deg) scale(1.05);
    filter: drop-shadow(0 0 11px #00eaff73);
  }
  .accent-dot { color: var(--accent); }
  .site-nav { display: flex; align-items: center; gap: 12px; }
  .header-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 42px;
    padding: 9px 17px;
    border: 1px solid var(--line);
    border-radius: 99px;
    background: #ffffff08;
    color: var(--ink);
    font-size: 13px;
    font-weight: 600;
    transition: background .2s;
  }
  .header-button:hover { background: #ffffff15; }
  .theme-toggle { width: 42px; padding: 0; flex-shrink: 0; }
  @media (max-width: 640px) {
    .site-header { width: calc(100% - 24px); margin-top: 12px; min-height: 64px; padding: 10px 14px; gap: 8px; }
    .brand-link { font-size: clamp(14px, 4.2vw, 22px); gap: 8px; }
    .brand-link img { width: 42px; height: 28px; }
    .site-nav { gap: 6px; }
    .header-button { padding: 9px 11px; font-size: 11px; }
    .desktop-link { display: none; }
    .theme-toggle { width: 36px; min-height: 36px; padding: 0; }
  }
  @media (prefers-reduced-motion: reduce) {
    .brand-link img, .header-button { transition: none; }
    .brand-link:hover img, .brand-link:focus-visible img { transform: none; }
  }
</style>
