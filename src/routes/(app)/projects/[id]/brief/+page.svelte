<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, type Brief, type Dimension, type ProjectDetail, type Score } from '$lib/api';
	import { VERDICT_ON_DARK } from '$lib/colours';
	import { TOTAL_QUESTIONS, VERDICT_LABELS } from '$lib/scoring';
	import { session } from '$lib/session.svelte';
	import { DIM_SHORT, formatDateTime, formatScore, joinAnd } from '$lib/text';

	const id = $derived(page.params.id ?? '');

	let project = $state<ProjectDetail | null>(null);
	let dims = $state<Dimension[]>([]);
	let briefs = $state<Brief[]>([]);
	let selected = $state('');
	let error = $state('');
	let notice = $state('');
	let busy = $state<'' | 'write' | 'approve'>('');

	$effect(() => {
		const pid = id;
		error = '';
		project = null;
		Promise.all([
			api<ProjectDetail>(`/projects/${pid}`),
			api<Dimension[]>('/questions'),
			api<Brief[]>(`/projects/${pid}/briefs`)
		])
			.then(([p, d, b]) => {
				project = p;
				dims = d;
				briefs = b;
				selected = b[0]?.id ?? '';
			})
			.catch((e) => (error = e instanceof Error ? e.message : String(e)));
	});

	const brief = $derived(briefs.find((b) => b.id === selected) ?? null);
	const isLatest = $derived(!!brief && brief.id === briefs[0]?.id);
	const canWrite = $derived(!!project?.can_edit && !project.archived);
	const canApprove = $derived(
		session.user?.role === 'approver' && !!brief && !brief.approved && !project?.archived
	);
	// The verdict always comes from the rules: the brief's snapshot, else the live result.
	const shown = $derived<Score | null>(
		brief
			? {
					dimensions: brief.dimensions,
					lowest: brief.lowest,
					weakest: brief.weakest,
					verdict: brief.verdict,
					answered: brief.answered,
					coverage: brief.answered / TOTAL_QUESTIONS,
					partial: brief.answered < TOTAL_QUESTIONS
				}
			: (project?.score ?? null)
	);
	const titles = $derived(Object.fromEntries(dims.map((d) => [d.id, d.title])));
	const questionText = $derived(
		Object.fromEntries(dims.flatMap((d) => d.questions.map((q) => [q.id, q.text])))
	);
	const open = $derived(shown ? TOTAL_QUESTIONS - shown.answered : 0);

	async function write() {
		busy = 'write';
		error = '';
		notice = '';
		try {
			const b = await api<Brief>(`/projects/${id}/briefs`, { method: 'POST' });
			briefs = [b, ...briefs];
			selected = b.id;
			notice = 'The AI wrote a new brief. The verdict and scores come from the rules.';
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = '';
		}
	}

	async function approve() {
		if (!brief) return;
		const warn = brief.changed_since
			? ' Answers changed after this brief was written, so it may not show the latest result.'
			: '';
		if (!confirm(`Approve this decision: "${VERDICT_LABELS[brief.verdict]}"?${warn}`)) return;
		busy = 'approve';
		error = '';
		notice = '';
		try {
			const b = await api<Brief>(`/briefs/${brief.id}/approve`, { method: 'POST' });
			briefs = briefs.map((x) => (x.id === b.id ? b : x));
			notice = 'Decision approved.';
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = '';
		}
	}

	function versionLabel(b: Brief, i: number): string {
		const n = briefs.length - i;
		return `Version ${n} · ${formatDateTime(b.created_at)}${b.approved ? ' · approved' : ''}`;
	}

	const BAR = { weak: 'bg-weak', partial: 'bg-partial', strong: 'bg-strong', none: 'bg-line' };
</script>

<svelte:head>
	<title>{project ? `${project.name} · ` : ''}Decision brief · City Prism</title>
</svelte:head>

{#if error && !project}
	<main class="p-6">
		<p role="alert" class="border-l-4 border-weak bg-panel p-4">{error}</p>
		<a href={resolve('/')} class="mt-4 inline-block text-teal underline">Back to the portfolio</a>
	</main>
{:else if !project || !shown}
	<p class="p-6 text-muted">Loading the decision brief…</p>
{:else}
	<!-- Dark band: the rules result -->
	<section class="band bg-navy px-4 pt-5 pb-7 text-band-ink sm:px-7">
		<nav aria-label="Breadcrumb" class="text-sm text-band-muted">
			<a href={resolve('/')} class="text-band-muted underline-offset-4 hover:underline">Portfolio</a
			>
			/
			<a
				href={resolve(`/projects/${project.id}`)}
				class="text-band-muted underline-offset-4 hover:underline">{project.name}</a
			>
			/ <span class="text-white">Decision brief</span>
		</nav>

		<div class="mt-4 flex flex-wrap items-end justify-between gap-6">
			<div>
				<p class="font-mono text-xs tracking-[0.04em] text-teal-on-dark">
					{project.name.toUpperCase()} · {project.business_unit || 'No business unit'} · {project.stage}
				</p>
				<p class="mt-3 text-sm text-band-muted">Verdict from the rules</p>
				<h1
					class="font-condensed text-4xl leading-tight font-semibold sm:text-6xl"
					style:color={VERDICT_ON_DARK[shown.verdict]}
				>
					{VERDICT_LABELS[shown.verdict]}
				</h1>
				<p class="mt-3 flex flex-wrap items-center gap-3 text-sm">
					{#if shown.partial}
						<span
							class="border border-partial-on-dark px-2 py-0.5 font-mono text-xs text-partial-on-dark"
							>Partial: {shown.answered} of {TOTAL_QUESTIONS} answered</span
						>
					{/if}
					{#if shown.lowest !== null}
						<span
							>Weakest link: <strong class="text-white"
								>{joinAnd(shown.weakest.map((d) => titles[d] ?? DIM_SHORT[d]))}</strong
							>
							<span class="font-mono text-white">{formatScore(shown.lowest)}</span> of 5</span
						>
					{/if}
				</p>
			</div>

			<div class="flex w-full flex-col gap-2 sm:w-auto sm:min-w-64">
				{#if briefs.length > 1}
					<label class="text-sm text-band-muted" for="version">Brief version</label>
					<select
						id="version"
						class="min-h-11 border border-band-line bg-band-raised px-2 text-white"
						bind:value={selected}
					>
						{#each briefs as b, i (b.id)}<option value={b.id}>{versionLabel(b, i)}</option>{/each}
					</select>
				{/if}
				{#if canWrite}
					<button type="button" class="btn-primary" onclick={write} disabled={!!busy}>
						{busy === 'write'
							? 'The AI is writing…'
							: briefs.length
								? 'Rewrite brief'
								: 'Write brief with AI'}
					</button>
				{/if}
				{#if canApprove}
					<button
						type="button"
						class="min-h-11 bg-strong-on-dark px-4 text-sm font-semibold text-navy hover:bg-strong-on-dark-hover disabled:opacity-55"
						onclick={approve}
						disabled={!!busy}>{busy === 'approve' ? 'Approving…' : 'Approve decision'}</button
					>
				{/if}
			</div>
		</div>
	</section>

	<div aria-live="polite">
		{#if error}
			<p role="alert" class="border-b border-line bg-error-bg px-4 py-2 text-sm sm:px-7">
				{error}
			</p>
		{/if}
		{#if notice}
			<p role="status" class="border-b border-line bg-panel px-4 py-2 text-sm sm:px-7">{notice}</p>
		{/if}
	</div>
	{#if project.archived}
		<p class="border-b border-line bg-warn-bg px-4 py-2 text-sm sm:px-7">
			This project is archived. Its briefs are kept but cannot be changed or approved.
		</p>
	{/if}

	<main class="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-7">
		{#if !brief}
			<section class="border border-line bg-panel p-5">
				<h2 class="text-lg font-semibold">No brief yet</h2>
				<p class="mt-2 max-w-2xl text-muted">
					{#if shown.verdict === 'not_assessed'}
						Answer at least one question first. Then the AI can write a headline, a short summary,
						up to 3 actions and the main risks.
					{:else if canWrite}
						The AI writes a headline, a short summary, up to 3 actions and the main risks from the
						answers. The verdict and scores above come from the rules and do not change.
					{:else}
						Nobody has written a brief for this project yet. The project owner, reviewers and admins
						can write one.
					{/if}
				</p>
			</section>
		{:else}
			{#if brief.approved}
				<p class="border-l-4 border-strong bg-panel p-3">
					<strong>Approved</strong> by {brief.approved_by?.name ?? 'an approver'}
					{#if brief.approved_at}on {formatDateTime(brief.approved_at)}{/if}.
				</p>
			{/if}
			{#if brief.changed_since}
				<p class="border-l-4 border-partial bg-panel p-3">
					Answers changed after this brief was written, so it may not show the latest result.
					{#if canWrite && isLatest}Rewrite it to update.{/if}
				</p>
			{/if}
			{#if !isLatest}
				<p class="border-l-4 border-line bg-panel p-3 text-muted">
					You are looking at an older version.
					<button
						type="button"
						class="min-h-11 text-teal underline underline-offset-4"
						onclick={() => (selected = briefs[0].id)}>Show the latest</button
					>
				</p>
			{/if}

			<section class="bg-ai-bg p-5 text-ai-ink sm:p-6" aria-labelledby="headline">
				<p class="font-mono text-xs font-semibold tracking-[0.06em]">
					WRITTEN BY AI · {formatDateTime(brief.created_at)}{brief.created_by
						? ` · asked by ${brief.created_by.name}`
						: ''}
				</p>
				<h2 id="headline" class="mt-2 font-condensed text-2xl font-semibold text-ink sm:text-3xl">
					{brief.headline}
				</h2>
				<p class="mt-3 max-w-3xl text-[17px] leading-relaxed text-ink">{brief.summary}</p>
			</section>
		{/if}

		<div class="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
			<section class="border border-line bg-panel p-5" aria-labelledby="scores-title">
				<h2 id="scores-title" class="font-semibold">Scores by dimension</h2>
				<p class="mt-1 text-sm text-muted">From the rules. Out of 5. The weakest is in bold.</p>
				<ul class="mt-4 space-y-3">
					{#each shown.dimensions as d (d.id)}
						{@const weak = shown.weakest.includes(d.id)}
						<li class="grid grid-cols-[minmax(0,10rem)_1fr_2.5rem] items-center gap-3 text-sm">
							<span class:font-semibold={weak}>{d.id}. {titles[d.id] ?? DIM_SHORT[d.id]}</span>
							<span class="h-3 bg-canvas">
								<span
									class="block h-3 {BAR[d.band]}"
									style:width="{d.score === null ? 0 : (d.score / 5) * 100}%"
								></span>
							</span>
							<span class="text-right font-mono" class:font-semibold={weak}
								>{d.score === null ? '—' : formatScore(d.score)}</span
							>
						</li>
					{/each}
				</ul>
			</section>

			{#if brief}
				<div class="space-y-6">
					<section aria-labelledby="actions-title">
						<h2 id="actions-title" class="font-semibold">Top actions</h2>
						{#if brief.actions.length === 0}
							<p class="mt-2 text-sm text-muted">The AI suggested no actions.</p>
						{/if}
						<ol class="mt-3 grid gap-3">
							{#each brief.actions as a, i (i)}
								{@const dimId = Number(a.question_id.split('.')[0])}
								<li class="border border-line bg-panel p-4">
									<p class="font-mono text-xs text-muted" title={questionText[a.question_id]}>
										<span class="font-semibold text-teal">{a.question_id}</span> · {titles[dimId] ??
											DIM_SHORT[dimId]}
									</p>
									<p class="mt-1 font-medium">{a.action}</p>
									<p class="mt-1 text-sm text-muted">Owner: {a.owner}</p>
								</li>
							{/each}
						</ol>
					</section>

					<section aria-labelledby="risks-title">
						<h2 id="risks-title" class="font-semibold">Risks</h2>
						{#if brief.risks.length === 0}
							<p class="mt-2 text-sm text-muted">The AI named no risks.</p>
						{:else}
							<ul class="mt-2 list-disc space-y-1 pl-5">
								{#each brief.risks as r, i (i)}<li>{r}</li>{/each}
							</ul>
						{/if}
					</section>
				</div>
			{/if}
		</div>

		{#if open > 0}
			<p class="border-l-4 border-partial bg-panel p-3">
				{open === 1 ? '1 question is' : `${open} questions are`} still open. The verdict can change as
				they are answered.
			</p>
		{/if}

		<div class="flex flex-wrap gap-3 border-t border-line pt-5">
			<button type="button" class="btn" disabled title="Coming later">Export PDF</button>
			<button type="button" class="btn" disabled title="Coming later"
				>Send to steering committee</button
			>
			<span class="self-center text-sm text-muted">Coming later.</span>
		</div>

		<p class="text-sm text-muted">
			The AI writes the summary and actions from the answers. The verdict and scores come from fixed
			rules, so every project is judged the same way.
		</p>
	</main>
{/if}
