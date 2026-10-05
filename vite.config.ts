import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		// In development the API runs on uvicorn at 8080.
		proxy: { '/api': 'http://127.0.0.1:8080' }
	},
	test: {
		include: ['src/**/*.test.ts']
	}
});
