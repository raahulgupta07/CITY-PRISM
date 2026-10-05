<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { api, ROLE_LABELS } from '$lib/api';
	import { menu } from '$lib/menu';
	import { loadSession, session } from '$lib/session.svelte';
	import { setTheme, theme, THEME_LABELS, type ThemeChoice } from '$lib/theme.svelte';

	let { children } = $props();
	let error = $state('');

	onMount(async () => {
		try {
			if (!(await loadSession())) await goto(resolve('/signin'));
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	async function signOut() {
		await api('/auth/logout', { method: 'POST' });
		session.user = null;
		await goto(resolve('/signin'));
	}

	const mine = $derived(page.url.searchParams.get('mine') === '1');
	const nav = $derived([
		{ href: resolve('/'), label: 'Portfolio', on: page.url.pathname === '/' && !mine },
		{ href: resolve('/?mine=1'), label: 'My projects', on: page.url.pathname === '/' && mine },
		...(session.user?.role === 'admin'
			? [{ href: resolve('/admin'), label: 'Admin', on: page.url.pathname.startsWith('/admin') }]
			: [])
	]);
</script>

<a
	href="#main"
	class="sr-only z-50 bg-panel p-3 text-ink focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
	>Skip to content</a
>
<header class="band border-b border-band-edge bg-navy text-band-ink">
	<div class="flex min-h-12 flex-wrap items-center gap-x-4 px-4 sm:px-5">
		<a
			href={resolve('/')}
			class="flex min-h-11 items-center font-condensed text-base font-semibold tracking-[0.06em] text-white uppercase no-underline"
			>City Prism</a
		>
		<nav
			aria-label="Main"
			class="order-last -mx-3 flex w-full gap-1 self-stretch sm:order-none sm:mx-0 sm:w-auto sm:flex-1"
		>
			{#each nav as item (item.label)}
				<a
					href={item.href}
					aria-current={item.on ? 'page' : undefined}
					class="flex min-h-11 items-center px-3 text-sm no-underline {item.on
						? 'text-white shadow-[inset_0_-2px_0_var(--color-teal-on-dark)]'
						: 'text-band-muted hover:text-white'}">{item.label}</a
				>
			{/each}
		</nav>
		{#if session.user}
			<details class="account relative ml-auto sm:ml-0" use:menu>
				<summary
					class="flex min-h-11 cursor-pointer list-none items-center gap-2 px-2 text-sm text-band-ink hover:text-white"
				>
					<span>{session.user.name}</span>
					<span class="text-band-muted">· {ROLE_LABELS[session.user.role].toLowerCase()}</span>
					<span aria-hidden="true" class="text-band-muted">▾</span>
				</summary>
				<div
					class="absolute right-0 z-30 mt-1 w-64 border border-line bg-panel p-3 text-ink shadow-md"
				>
					<p class="text-sm font-semibold">{session.user.name}</p>
					<p class="text-sm break-all text-muted">{session.user.email}</p>
					<fieldset class="mt-3 border-t border-line pt-3">
						<legend class="label">Theme</legend>
						{#each Object.entries(THEME_LABELS) as [value, label] (value)}
							<label class="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
								<input
									type="radio"
									name="theme"
									class="size-4 accent-teal"
									checked={theme.choice === value}
									onchange={() => setTheme(value as ThemeChoice)}
								/>
								{label}
							</label>
						{/each}
					</fieldset>
					<button type="button" class="btn mt-2 w-full" onclick={signOut}>Sign out</button>
				</div>
			</details>
		{/if}
	</div>
</header>

<div id="main" tabindex="-1" class="outline-none">
	{#if error}
		<p role="alert" class="m-6 border-l-4 border-weak bg-panel p-4">{error}</p>
	{:else if session.user}
		{@render children()}
	{:else}
		<p class="p-6 text-muted">Loading…</p>
	{/if}
</div>

<style>
	.account summary::-webkit-details-marker {
		display: none;
	}
</style>
