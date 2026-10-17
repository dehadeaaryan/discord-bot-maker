<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { Sun, Moon, ArrowUpRight } from '@lucide/svelte';
  let { children } = $props();
  let light = $state(false);
  onMount(() => { light = localStorage.getItem('dbm-theme') === 'light'; document.documentElement.classList.toggle('light', light); });
  function toggle() { light = !light; localStorage.setItem('dbm-theme', light ? 'light' : 'dark'); document.documentElement.classList.toggle('light', light); }
</script>
<svelte:head><meta name="theme-color" content="#171514" /></svelte:head>
<a class="skip-link" href="#main">Skip to content</a>
<div class="ambient" aria-hidden="true"></div>
<header class="site-header">
  <a class="brand" href="/"><img src="/favicon.svg" width="34" height="34" alt=""/><span>Bot Maker<span class="orange">.</span></span></a>
  <nav aria-label="Main navigation"><a href="/help">Guide</a><a class="desktop-link" href="https://github.com/dehadeaaryan/discord-bot-maker">Python library <ArrowUpRight size={13}/></a><button class="icon-button" onclick={toggle} aria-label={light ? 'Switch to dark theme' : 'Switch to light theme'}>{#if light}<Moon size={17}/>{:else}<Sun size={17}/>{/if}</button></nav>
</header>
{@render children()}
