<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { api, ROLE_LABELS, type AuthOptions, type User } from '$lib/api';

	let options = $state<AuthOptions | null>(null);
	let error = $state('');
	let busy = $state(false);

	onMount(async () => {
		try {
			options = await api<AuthOptions>('/auth/options');
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	async function signIn(email: string) {
		busy = true;
		error = '';
		try {
			await api<User>('/auth/login', { method: 'POST', body: JSON.stringify({ email }) });
			await goto(resolve('/'));
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
</script>

<div class="band flex min-h-screen flex-col bg-navy text-white">
	<main class="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-10">
		<p class="font-mono text-xs tracking-[0.08em] text-teal-on-dark">CITY HOLDINGS · CITY AI</p>
		<h1 class="mt-2 font-condensed text-4xl font-semibold">City Prism</h1>
		<p class="mt-2 text-band-soft">Check if each AI project is ready for its next stage.</p>

		{#if error}
			<p role="alert" class="mt-6 border-l-4 border-weak bg-panel p-3 text-ink">{error}</p>
		{/if}

		{#if options?.provider === 'dev'}
			<section class="mt-8 bg-panel p-5 text-ink" aria-labelledby="dev-title">
				<h2 id="dev-title" class="font-semibold">Sign in as</h2>
				<p class="mt-1 text-sm text-muted">Test sign-in. Company sign-in replaces this later.</p>
				<ul class="mt-4 divide-y divide-line border-y border-line">
					{#each options.users as u (u.email)}
						<li>
							<button
								class="flex min-h-11 w-full items-center justify-between gap-3 px-1 py-2 text-left hover:bg-canvas disabled:opacity-60"
								disabled={busy}
								onclick={() => signIn(u.email)}
							>
								<span>
									<span class="block font-medium">{u.name}</span>
									<span class="block text-sm text-muted">{u.email}</span>
								</span>
								<span class="font-mono text-xs text-teal">{ROLE_LABELS[u.role]}</span>
							</button>
						</li>
					{/each}
				</ul>
			</section>
		{:else if options}
			<p class="mt-8 bg-panel p-4 text-ink">
				Company sign-in is not set up yet. Please contact the City AI team.
			</p>
		{/if}
	</main>
</div>
