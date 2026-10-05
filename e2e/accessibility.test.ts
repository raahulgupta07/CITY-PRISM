import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

// Automated accessibility checks (WCAG 2.1 AA: contrast, labels, roles) on every
// screen, in both themes. A person still needs to check with a screen reader.

for (const scheme of ['light', 'dark'] as const) {
	test(`no accessibility problems in the ${scheme} theme`, async ({ page }) => {
		await page.emulateMedia({ colorScheme: scheme });
		await page.goto('/signin');
		await expect(page.getByRole('heading', { name: 'Sign in as' })).toBeVisible();

		const check = async (label: string) => {
			const result = await new AxeBuilder({ page })
				.withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
				.analyze();
			const problems = result.violations.map(
				(v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`
			);
			expect(result.passes.length, 'axe ran').toBeGreaterThan(10);
			expect(problems, `${label} (${scheme})`).toEqual([]);
		};
		await check('sign in');

		await page.getByRole('button', { name: /Rahul Gupta/ }).click();
		await expect(page.getByRole('link', { name: 'Employee Assistant' }).first()).toBeVisible();
		await check('portfolio');

		await page.getByRole('link', { name: 'Employee Assistant' }).first().click();
		await expect(page.getByRole('tab', { name: 'Interview' })).toBeVisible();
		await check('assess');

		await page.getByRole('tab', { name: 'Read evidence' }).click();
		await check('read evidence');

		await page.getByRole('link', { name: 'Decision brief →' }).click();
		await expect(page.getByText('Verdict from the rules')).toBeVisible();
		await check('decision brief');

		await page.goto('/projects/new');
		await expect(page.getByLabel(/Project name/)).toBeVisible();
		await check('new project');

		await page.goto('/admin');
		await expect(page.getByRole('tab', { name: 'Question set' })).toBeVisible();
		await check('admin questions');
		await page.getByRole('tab', { name: 'Users and roles' }).click();
		await check('admin users');
	});
}
