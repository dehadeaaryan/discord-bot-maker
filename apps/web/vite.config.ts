import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default defineConfig(({ command }) => ({
  plugins: [sveltekit({
    adapter: adapter(),
    preprocess: vitePreprocess(),
    paths: { origin: process.env.PUBLIC_ORIGIN || process.env.ORIGIN || 'http://localhost:5173' },
    csp: {
      mode: 'auto',
      directives: {
        'default-src': ['self'],
        'script-src': ['self'],
        // The graph canvas positions nodes using inline styles.
        'style-src': ['self', 'unsafe-inline'],
        'img-src': ['self', 'data:', 'blob:'],
        'font-src': ['self'],
        'connect-src': command === 'serve' ? ['self', 'ws:', 'wss:'] : ['self'],
        'object-src': ['none'],
        'base-uri': ['none'],
        'frame-ancestors': ['none'],
        'form-action': ['self']
      }
    }
  })]
}));
