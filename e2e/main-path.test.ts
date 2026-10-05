import { expect, test, type Page } from '@playwright/test';

// The main path from SPEC §13: sign in → new project → answer → interview →
// evidence → brief → approve → export. It runs at desktop and phone width.

async function signInAs(page: Page, name: RegExp) {
	await page.goto('/signin');
	await page.getByRole('button', { name }).click();
	await expect(page.getByRole('navigation', { name: 'Main' })).toBeVisible();
}

async function signOut(page: Page) {
	await page.locator('details.account summary').click();
	await page.getByRole('button', { name: 'Sign out' }).click();
	await expect(page.getByRole('heading', { name: 'Sign in as' })).toBeVisible();
}

test('owner assesses a project, approver approves, admin exports', async ({ page }, info) => {
	const name = `Sales Forecast ${info.project.name}`;
	const errors: string[] = [];
	page.on('pageerror', (e) => errors.push(String(e)));
	page.on('dialog', (d) => d.accept());

	// Sign in as the owner and create a project.
	await signInAs(page, /Test Owner/);
	await expect(page.getByRole('heading', { level: 1 })).toContainText(/project/i);
	await page.getByRole('link', { name: 'New project' }).click();
	await page.getByLabel(/Project name/).fill(name);
	await page.getByLabel('Business unit').fill('Retail');
	await page.getByRole('button', { name: 'Create and start' }).click();
	await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();
	await expect(page.getByText('Not assessed', { exact: true })).toBeVisible();

	// Answer 1.2 by hand: the verdict comes from the rules at once.
	const answer12 = page.getByRole('group', { name: 'Answer for 1.2' });
	await answer12.getByRole('button', { name: 'Yes' }).click();
	await expect(answer12.getByRole('button', { name: 'Yes' })).toHaveAttribute(
		'aria-pressed',
		'true'
	);
	await expect(page.getByText('Saved').first()).toBeVisible();

	// Interview: the agent asks 1.1 and records the reply as an AI answer.
	await page.getByRole('tab', { name: 'Interview' }).click();
	await page.getByRole('button', { name: 'Start interview' }).click();
	await page.getByLabel('Answer in your own words').fill('We will produce a weekly forecast.');
	await page.getByRole('button', { name: /Send/ }).click();
	await expect(page.getByText('RECORDED 1.1')).toBeVisible();
	await expect(page.getByText('AI SUGGESTED · NOT CONFIRMED').first()).toBeVisible();
	await page.getByRole('button', { name: 'Stop' }).click();

	// Undo is offered for the last agent answer; confirm keeps it instead.
	await expect(page.getByRole('button', { name: 'Undo' })).toBeVisible();
	await page.getByRole('button', { name: 'Confirm' }).first().click();
	await expect(page.getByText('AI SUGGESTED · NOT CONFIRMED')).toHaveCount(0);

	// Read evidence: the AI suggests 3.1, the owner accepts it.
	await page.getByRole('tab', { name: 'Read evidence' }).click();
	await page
		.getByLabel(/Paste text/)
		.fill('Sales data exists in the warehouse but it has not been cleaned yet.');
	await page.getByRole('button', { name: 'Read evidence' }).click();
	await expect(page.getByText(/Found 1 possible answer/)).toBeVisible();
	await page.getByRole('button', { name: 'Accept', exact: true }).click();
	await expect(page.getByRole('tab', { name: /3 Data/ })).toBeVisible();

	// Every change is in the history.
	await page.getByRole('tab', { name: 'Changes' }).click();
	await expect(page.locator('#agent-panel li')).toHaveCount(4);

	// Decision brief: the verdict comes from the rules, the AI writes the words.
	await page.getByRole('link', { name: 'Decision brief →' }).click();
	await expect(page.getByRole('heading', { level: 1, name: 'Go with actions' })).toBeVisible();
	await page.getByRole('button', { name: 'Write brief with AI' }).click();
	await expect(page.getByText(/can go ahead once the data is cleaned/)).toBeVisible();
	await expect(page.getByText('Clean the sales data.')).toBeVisible();
	await expect(page.getByRole('button', { name: 'Approve decision' })).toHaveCount(0);
	const briefUrl = page.url();
	await signOut(page);

	// The approver approves.
	await signInAs(page, /Test Approver/);
	await page.goto(briefUrl);
	await page.getByRole('button', { name: 'Approve decision' }).click();
	await expect(page.getByText(/Approved\s+by Test Approver/)).toBeVisible();
	await signOut(page);

	// The admin exports the portfolio.
	await signInAs(page, /Rahul Gupta/);
	await page.locator('details.export summary').click();
	const [xlsx] = await Promise.all([
		page.waitForEvent('download'),
		page.getByRole('link', { name: /Excel/ }).click()
	]);
	expect(xlsx.suggestedFilename()).toMatch(/^city-prism-portfolio-\d{4}-\d{2}-\d{2}\.xlsx$/);
	await page.locator('details.export summary').click();
	const [csv] = await Promise.all([
		page.waitForEvent('download'),
		page.getByRole('link', { name: /CSV/ }).click()
	]);
	const text = await (await csv.createReadStream()).toArray();
	expect(Buffer.concat(text).toString('utf8')).toContain(name);

	expect(errors).toEqual([]);
});

test('the theme can follow the system or be set by hand', async ({ page }) => {
	await page.emulateMedia({ colorScheme: 'dark' });
	await signInAs(page, /Test Owner/);
	const html = page.locator('html');
	await expect(html).toHaveAttribute('data-theme', 'dark');

	await page.locator('details.account summary').click();
	await page.getByRole('radio', { name: 'Light' }).check();
	await expect(html).toHaveAttribute('data-theme', 'light');
	await page.reload();
	await expect(html).toHaveAttribute('data-theme', 'light');

	await page.locator('details.account summary').click();
	await page.getByRole('radio', { name: 'Follow the system' }).check();
	await expect(html).toHaveAttribute('data-theme', 'dark');
});

test('screens fit a phone without sideways scrolling', async ({ page }, info) => {
	test.skip(info.project.name !== 'phone', 'phone only');
	await signInAs(page, /Rahul Gupta/);
	for (const path of ['/', '/projects/new', '/admin']) {
		await page.goto(path);
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
		expect(overflow, path).toBeLessThanOrEqual(0);
	}
	await page.goto('/');
	await page.getByRole('link', { name: 'Employee Assistant' }).click();
	await expect(page.getByRole('tab', { name: /Ownership/ })).toBeVisible();
	const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
	expect(overflow).toBeLessThanOrEqual(0);
});
