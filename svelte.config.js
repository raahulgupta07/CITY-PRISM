import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		// Single-page app: FastAPI serves build/ and falls back to index.html.
		adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html' })
	}
};

export default config;
