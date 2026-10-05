<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import {
		api,
		DUE_DATE,
		MODE_LABELS,
		ROLE_LABELS,
		STAGES,
		type Mode,
		type Project,
		type ProjectDetail,
		type Stage,
		type User
	} from '$lib/api';
	import { session } from '$lib/session.svelte';

	let users = $state<User[]>([]);
	let businessUnits = $state<string[]>([]);
	let name = $state('');
	let businessUnit = $state('');
	let sponsor = $state('');
	let ownerId = $state(session.user?.id ?? '');
	let stage = $state<Stage>('Idea');
	let mode = $state<Mode>('plan');
	let dueDate = $state('');
	let error = $state('');
	let nameError = $state('');
	let busy = $state(false);

	const canCreate = $derived(session.user?.role !== 'approver');

	onMount(async () => {
		try {
			const [u, projects] = await Promise.all([api<User[]>('/users'), api<Project[]>('/projects')]);
			users = u;
			businessUnits = [...new Set(projects.map((p) => p.business_unit).filter(Boolean))].sort();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	function setMode(m: Mode) {
		mode = m;
		// Existing projects must be assessed by 30 Oct 2026.
		if (m === 'assess' && !dueDate) dueDate = DUE_DATE;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		nameError = name.trim() ? '' : 'Enter a project name.';
		if (nameError) {
			document.getElementById('name')?.focus();
			return;
		}
		busy = true;
		error = '';
		try {
			const created = await api<ProjectDetail>('/projects', {
				method: 'POST',
				body: JSON.stringify({
					name,
					business_unit: businessUnit,
					sponsor,
					owner_user_id: ownerId || null,
					stage,
					mode,
					due_date: dueDate || null
				})
			});
			await goto(resolve(`/projects/${created.id}`));
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			busy = false;
		}
	}
</script>

<svelte:head><title>New project · City Prism</title></svelte:head>

<main class="mx-auto max-w-2xl px-4 py-8 sm:px-6">
	<nav aria-label="Breadcrumb" class="text-sm text-muted">
		<a href={resolve('/')} class="text-muted underline-offset-4 hover:underline">Portfolio</a> / New project
	</nav>
	<h1 class="mt-2 font-condensed text-3xl font-semibold">New project</h1>
	<p class="mt-1 text-muted">After you create it, you can answer the 40 questions.</p>

	{#if !canCreate}
		<p class="mt-6 border-l-4 border-partial bg-panel p-4">
			Your role can read projects but cannot create them.
		</p>
	{:else}
		<form
			class="mt-6 space-y-5 border border-line bg-panel p-5 sm:p-6"
			onsubmit={submit}
			novalidate
		>
			{#if error}
				<p role="alert" class="border-l-4 border-weak bg-[#FBEAEA] p-3">{error}</p>
			{/if}

			<div>
				<label class="label" for="name"
					>Project name <span class="text-weak">(required)</span></label
				>
				<input
					id="name"
					class="field w-full"
					bind:value={name}
					oninput={() => (nameError = '')}
					maxlength="200"
					aria-invalid={nameError ? 'true' : undefined}
					aria-describedby={nameError ? 'name-error' : undefined}
				/>
				{#if nameError}<p id="name-error" class="mt-1 text-sm text-weak">{nameError}</p>{/if}
			</div>

			<div class="grid gap-5 sm:grid-cols-2">
				<div>
					<label class="label" for="bu">Business unit</label>
					<input
						id="bu"
						class="field w-full"
						list="bu-list"
						bind:value={businessUnit}
						maxlength="200"
					/>
					<datalist id="bu-list">
						{#each businessUnits as bu (bu)}<option value={bu}></option>{/each}
					</datalist>
				</div>
				<div>
					<label class="label" for="sponsor">Sponsor</label>
					<input id="sponsor" class="field w-full" bind:value={sponsor} maxlength="200" />
				</div>
				<div>
					<label class="label" for="owner">Project owner</label>
					<select id="owner" class="field w-full" bind:value={ownerId}>
						{#each users as u (u.id)}
							<option value={u.id}>{u.name} · {ROLE_LABELS[u.role]}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="label" for="stage">Stage</label>
					<select id="stage" class="field w-full" bind:value={stage}>
						{#each STAGES as s (s)}<option value={s}>{s}</option>{/each}
					</select>
				</div>
			</div>

			<fieldset>
				<legend class="label">Purpose of this check</legend>
				<div class="grid gap-2 sm:grid-cols-2">
					{#each ['plan', 'assess'] as const as m (m)}
						<label
							class="flex min-h-11 cursor-pointer items-center gap-3 border px-3 {mode === m
								? 'border-ink'
								: 'border-line'}"
						>
							<input
								type="radio"
								name="mode"
								value={m}
								checked={mode === m}
								onchange={() => setMode(m)}
								class="size-4 accent-ink"
							/>
							{MODE_LABELS[m]}
						</label>
					{/each}
				</div>
			</fieldset>

			<div class="sm:w-1/2">
				<label class="label" for="due">Due date</label>
				<input id="due" type="date" class="field w-full" bind:value={dueDate} />
			</div>

			<div class="flex flex-wrap gap-3 border-t border-line pt-5">
				<button type="submit" class="btn-primary" disabled={busy}>
					{busy ? 'Creating…' : 'Create and start'}
				</button>
				<a href={resolve('/')} class="btn">Cancel</a>
			</div>
		</form>
	{/if}
</main>
