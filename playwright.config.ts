import { defineConfig, devices } from '@playwright/test';

// Browser tests for the main path. Run `npm run build` first, then `npm run test:e2e`.
// The AI is a local fake (e2e/fake_openrouter.py), so no key or internet is needed.
export default defineConfig({
	testDir: 'e2e',
	timeout: 60_000,
	fullyParallel: false,
	workers: 1,
	use: {
		baseURL: 'http://127.0.0.1:8081',
		trace: 'retain-on-failure'
	},
	projects: [
		{ name: 'desktop', use: { ...devices['Desktop Chrome'] } },
		{
			name: 'phone',
			use: {
				...devices['Desktop Chrome'],
				viewport: { width: 390, height: 844 },
				isMobile: true,
				hasTouch: true
			}
		}
	],
	webServer: {
		command: './e2e/serve.sh',
		url: 'http://127.0.0.1:8081/api/health',
		reuseExistingServer: false,
		timeout: 60_000
	}
});
