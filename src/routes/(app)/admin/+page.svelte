<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ROLE_LABELS, type Dimension, type Question, type Role, type User } from '$lib/api';
	import { session } from '$lib/session.svelte';

	const ROLES: Role[] = ['owner', 'reviewer', 'approver', 'admin'];

	let tab = $state<'questions' | 'users'>('questions');
	let dims = $state<Dimension[]>([]);
	let users = $state<User[]>([]);
	let error = $state('');
	let message = $state('');
	// Unsaved edits, by question ID or "dim-<id>".
	let edits = $state<Record<string, string>>({});

	let newName = $state('');
	let newEmail = $state('');
	let newRole = $state<Role>('owner');

	const isAdmin = $derived(session.user?.role === 'admin');

	onMount(async () => {
		if (!isAdmin) return;
		try {
			[dims, users] = await Promise.all([
				api<Dimension[]>('/questions'),
				api<User[]>('/admin/users')
			]);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	async function run(action: () => Promise<void>, done: string) {
		message = '';
		error = '';
		try {
			await action();
			message = done;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	function saveQuestion(q: Question, changes: { text?: string; is_draft?: boolean }) {
		run(async () => {
			const saved = await api<Question>(`/admin/questions/${q.id}`, {
				method: 'PUT',
				body: JSON.stringify(changes)
			});
			Object.assign(q, saved);
			delete edits[q.id];
		}, `Question ${q.id} saved.`);
	}

	function saveLead(d: Dimension) {
		run(async () => {
			const saved = await api<{ lead_question: string }>(`/admin/dimensions/${d.id}`, {
				method: 'PUT',
				body: JSON.stringify({ lead_question: edits[`dim-${d.id}`] })
			});
			d.lead_question = saved.lead_question;
			delete edits[`dim-${d.id}`];
		}, `Lead question for dimension ${d.id} saved.`);
	}

	function setRole(u: User, role: Role) {
		run(async () => {
			const saved = await api<User>(`/admin/users/${u.id}`, {
				method: 'PATCH',
				body: JSON.stringify({ role })
			});
			u.role = saved.role;
		}, `${u.name} is now ${ROLE_LABELS[role].toLowerCase()}.`).then(async () => {
			// Reload so a refused change shows the real role again.
			users = await api<User[]>('/admin/users');
		});
	}

	function addUser(event: SubmitEvent) {
		event.preventDefault();
		run(async () => {
			const u = await api<User>('/admin/users', {
				method: 'POST',
				body: JSON.stringify({ name: newName, email: newEmail, role: newRole })
			});
			users = [...users, u].sort((a, b) => a.name.localeCompare(b.name));
			newName = '';
			newEmail = '';
			newRole = 'owner';
		}, 'User added.');
	}
</script>

<svelte:head><title>Admin · City Prism</title></svelte:head>

<main class="mx-auto max-w-5xl px-4 py-8 sm:px-6">
	<h1 class="font-condensed text-3xl font-semibold">Admin</h1>

	{#if !isAdmin}
		<p class="mt-6 border-l-4 border-partial bg-panel p-4">Only admins can open this page.</p>
	{:else}
		<div role="tablist" aria-label="Admin sections" class="mt-5 flex border-b border-line">
			{#each [['questions', 'Question set'], ['users', 'Users and roles']] as const as [key, label] (key)}
				<button
					type="button"
					role="tab"
					aria-selected={tab === key}
					class="min-h-11 px-4 text-sm {tab === key
						? 'font-semibold shadow-[inset_0_-2px_0_var(--color-teal)]'
						: 'text-muted'}"
					onclick={() => (tab = key)}>{label}</button
				>
			{/each}
		</div>

		<div aria-live="polite" class="mt-4">
			{#if error}<p role="alert" class="border-l-4 border-weak bg-panel p-3">{error}</p>{/if}
			{#if message}<p class="border-l-4 border-strong bg-panel p-3">{message}</p>{/if}
		</div>

		{#if tab === 'questions'}
			<p class="mt-4 text-sm text-muted">
				Changes apply at once to every project. Changing the wording of a question makes a new
				version. Answers already given stay as they are.
			</p>
			{#each dims as d (d.id)}
				<section class="mt-6 border border-line bg-panel" aria-labelledby="dim-{d.id}">
					<div class="border-b border-line p-4">
						<p class="text-xs font-semibold tracking-[0.08em] text-muted uppercase">
							Dimension {d.id} · {d.group_name}
						</p>
						<h2 id="dim-{d.id}" class="text-lg font-semibold">{d.title}</h2>
						<label class="mt-2 block text-sm text-muted" for="lead-{d.id}">Lead question</label>
						<div class="mt-1 flex flex-col gap-2 sm:flex-row">
							<textarea
								id="lead-{d.id}"
								class="field min-h-11 flex-1"
								rows="2"
								value={edits[`dim-${d.id}`] ?? d.lead_question}
								oninput={(e) => (edits[`dim-${d.id}`] = e.currentTarget.value)}></textarea>
							<button
								type="button"
								class="btn self-start"
								disabled={edits[`dim-${d.id}`] === undefined ||
									edits[`dim-${d.id}`] === d.lead_question}
								onclick={() => saveLead(d)}>Save</button
							>
						</div>
					</div>
					<ul class="divide-y divide-[#E1E5EA]">
						{#each d.questions as q (q.id)}
							<li class="grid gap-2 p-4 sm:grid-cols-[3rem_1fr_auto]">
								<label for="q-{q.id}" class="pt-2 font-mono font-semibold text-teal">{q.id}</label>
								<div>
									<textarea
										id="q-{q.id}"
										class="field w-full"
										rows="2"
										value={edits[q.id] ?? q.text}
										oninput={(e) => (edits[q.id] = e.currentTarget.value)}></textarea>
									<div class="mt-1 flex flex-wrap items-center gap-4 text-sm text-muted">
										<span class="font-mono text-xs">Version {q.version}</span>
										<label class="flex min-h-9 items-center gap-2">
											<input
												type="checkbox"
												class="size-4 accent-ink"
												checked={q.is_draft}
												onchange={(e) => saveQuestion(q, { is_draft: e.currentTarget.checked })}
											/>
											Draft wording
										</label>
									</div>
								</div>
								<button
									type="button"
									class="btn self-start"
									disabled={edits[q.id] === undefined || edits[q.id].trim() === q.text}
									onclick={() => saveQuestion(q, { text: edits[q.id] })}>Save</button
								>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		{:else}
			<div class="mt-4 overflow-x-auto">
				<table class="w-full min-w-[560px] border border-line bg-panel text-sm">
					<thead>
						<tr
							class="border-b border-ink text-left text-xs tracking-[0.06em] text-muted uppercase"
						>
							<th scope="col" class="px-3 py-2">Name</th>
							<th scope="col" class="px-3 py-2">Email</th>
							<th scope="col" class="px-3 py-2">Role</th>
						</tr>
					</thead>
					<tbody>
						{#each users as u (u.id)}
							<tr class="border-b border-[#E1E5EA] last:border-0">
								<td class="px-3 py-2">{u.name}</td>
								<td class="px-3 py-2 text-muted">{u.email}</td>
								<td class="px-3 py-1">
									<select
										class="field min-h-9 py-1"
										aria-label="Role for {u.name}"
										value={u.role}
										onchange={(e) => setRole(u, e.currentTarget.value as Role)}
									>
										{#each ROLES as r (r)}<option value={r}>{ROLE_LABELS[r]}</option>{/each}
									</select>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<form class="mt-6 border border-line bg-panel p-4" onsubmit={addUser}>
				<h2 class="font-semibold">Add a user</h2>
				<p class="mt-1 text-sm text-muted">
					Until company sign-in is connected, add people here so they can own projects.
				</p>
				<div class="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr_10rem_auto] sm:items-end">
					<div>
						<label class="label" for="new-name">Name</label>
						<input id="new-name" class="field w-full" bind:value={newName} required />
					</div>
					<div>
						<label class="label" for="new-email">Email</label>
						<input
							id="new-email"
							type="email"
							class="field w-full"
							bind:value={newEmail}
							required
						/>
					</div>
					<div>
						<label class="label" for="new-role">Role</label>
						<select id="new-role" class="field w-full" bind:value={newRole}>
							{#each ROLES as r (r)}<option value={r}>{ROLE_LABELS[r]}</option>{/each}
						</select>
					</div>
					<button type="submit" class="btn-primary">Add user</button>
				</div>
			</form>
		{/if}
	{/if}
</main>
