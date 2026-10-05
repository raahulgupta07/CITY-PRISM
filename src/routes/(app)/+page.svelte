<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, DUE_DATE, MODE_LABELS, type Mode, type Project } from '$lib/api';
	import ScoreCell from '$lib/components/ScoreCell.svelte';
	import SummaryPanel from '$lib/components/SummaryPanel.svelte';
	import VerdictMark from '$lib/components/VerdictMark.svelte';
	import { DIMENSION_IDS, VERDICT_LABELS, type Verdict } from '$lib/scoring';
	import { session } from '$lib/session.svelte';
	import {
		DIM_ABBR,
		DIM_SHORT,
		daysLeft,
		formatDate,
		formatScore,
		joinAnd,
		portfolioSentences,
		stuckCounts
	} from '$lib/text';

	let projects = $state<Project[]>([]);
	let loaded = $state(false);
	let error = $state('');
	let archivedOnly = $state(false);

	// Unchecked values per filter group. Empty means "show all".
	let hidden = $state<Record<string, string[]>>({ verdict: [], stage: [], bu: [], mode: [] });
	let owner = $state('');

	const mine = $derived(page.url.searchParams.get('mine') === '1');
	const canCreate = $derived(session.user?.role !== 'approver');
	const canExport = $derived(session.user?.role === 'admin');
	let showSummary = $state(false);

	$effect(() => {
		const query = archivedOnly ? '?archived=true' : '';
		loaded = false;
		api<Project[]>(`/projects${query}`)
			.then((rows) => {
				projects = rows;
				error = '';
			})
			.catch((e) => (error = e instanceof Error ? e.message : String(e)))
			.finally(() => (loaded = true));
	});

	function setMine(on: boolean) {
		goto(on ? resolve('/?mine=1') : resolve('/'), { keepFocus: true, noScroll: true });
	}

	function toggle(group: string, value: string) {
		const list = hidden[group];
		hidden[group] = list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
	}

	const visible = $derived(
		projects.filter(
			(p) =>
				!hidden.verdict.includes(p.score.verdict) &&
				!hidden.stage.includes(p.stage) &&
				!hidden.bu.includes(p.business_unit || '(none)') &&
				!hidden.mode.includes(p.mode) &&
				(!owner || p.owner?.id === owner) &&
				(!mine || p.owner?.id === session.user?.id)
		)
	);

	function countBy(key: (p: Project) => string): [string, number][] {
		const m: Record<string, number> = {};
		for (const p of projects) m[key(p)] = (m[key(p)] ?? 0) + 1;
		return Object.entries(m);
	}

	const VERDICTS: Verdict[] = ['fix', 'go', 'ready', 'not_assessed'];
	const MARK: Record<Verdict, string> = {
		fix: 'background:#B3261E',
		go: 'background:#C77C00',
		ready: 'background:#1F7A4C',
		not_assessed: 'border:1px solid #7A8494'
	};
	const verdictCounts = $derived(
		Object.fromEntries(
			VERDICTS.map((v) => [v, projects.filter((p) => p.score.verdict === v).length])
		)
	);
	const stageCounts = $derived(countBy((p) => p.stage));
	const buCounts = $derived(countBy((p) => p.business_unit || '(none)').sort());
	const modeCounts = $derived(countBy((p) => p.mode));
	const owners = $derived(
		[...new Map(projects.filter((p) => p.owner).map((p) => [p.owner!.id, p.owner!])).values()].sort(
			(a, b) => a.name.localeCompare(b.name)
		)
	);
	const stuck = $derived(stuckCounts(projects.map((p) => p.score)));
	const stuckMax = $derived(Math.max(1, ...stuck.map((s) => s.n)));
	const sentences = $derived(portfolioSentences(projects.map((p) => p.score)));
	const answered = $derived(projects.reduce((n, p) => n + p.score.answered, 0));
	const possible = $derived(projects.length * 40);
	const days = daysLeft(DUE_DATE);
	const daysText =
		days > 1
			? `${days} days left`
			: days === 1
				? '1 day left'
				: days === 0
					? 'due today'
					: 'due date passed';

	function weakText(p: Project): string {
		if (p.score.lowest === null) return '—';
		return `${joinAnd(p.score.weakest.map((d) => DIM_SHORT[d]))} ${formatScore(p.score.lowest)}`;
	}
</script>

<svelte:head><title>Portfolio · City Prism</title></svelte:head>

<!-- Dark band: headline from the rules, verdict counts, answered bar -->
<section class="bg-navy px-4 pt-8 pb-8 text-[#E6ECF2] sm:px-8" aria-labelledby="headline">
	<div class="flex flex-wrap items-end justify-between gap-8">
		<div class="max-w-3xl">
			<p class="font-mono text-xs tracking-[0.04em] text-teal-on-dark">
				Q1 FY27 · due {formatDate(DUE_DATE)} · {daysText}
			</p>
			{#if loaded}
				<h1
					id="headline"
					class="mt-4 font-condensed text-3xl leading-tight font-medium text-white sm:text-5xl"
				>
					{sentences.headline}
				</h1>
				<p class="mt-4 text-[17px] leading-relaxed text-[#C9D2DC]">{sentences.detail}</p>
			{:else}
				<h1 id="headline" class="mt-4 font-condensed text-3xl text-white">AI project portfolio</h1>
			{/if}
		</div>
		<div class="w-full max-w-md">
			<dl class="grid grid-cols-4 divide-x divide-[#2A3A52]">
				{#each [['fix', 'Fix', '#FF7A6B'], ['go', 'Go with actions', '#F5B84A'], ['ready', 'Ready', '#5FD39A'], ['not_assessed', 'Not assessed', '#FFFFFF']] as [v, label, colour] (v)}
					<div class="px-3 first:pl-0">
						<dd class="font-mono text-3xl" style:color={colour}>{verdictCounts[v] ?? 0}</dd>
						<dt class="text-xs leading-tight text-[#AEB9C6]">{label}</dt>
					</div>
				{/each}
			</dl>
			<div class="mt-5 flex items-center gap-3 text-sm">
				<span class="text-[#AEB9C6]">Answered</span>
				<div
					class="h-1 flex-1 bg-[#2A3A52]"
					role="progressbar"
					aria-label="Questions answered"
					aria-valuemin={0}
					aria-valuemax={possible}
					aria-valuenow={answered}
				>
					<div
						class="h-1 bg-teal-on-dark"
						style:width="{possible ? (answered / possible) * 100 : 0}%"
					></div>
				</div>
				<span class="font-mono text-xs"
					>{answered}/{possible} · {possible ? Math.round((answered / possible) * 100) : 0}%</span
				>
			</div>
		</div>
	</div>
</section>

<div class="flex flex-col lg:flex-row">
	<!-- Filter rail -->
	<aside
		class="border-b border-line bg-[#F7F8F9] px-4 py-5 lg:w-60 lg:shrink-0 lg:border-r lg:border-b-0"
		aria-label="Filters"
	>
		<fieldset>
			<legend class="rail-title">Verdict</legend>
			{#each VERDICTS as v (v)}
				<label class="rail-row">
					<input
						type="checkbox"
						checked={!hidden.verdict.includes(v)}
						onchange={() => toggle('verdict', v)}
					/>
					<span aria-hidden="true" class="size-2 shrink-0" style={MARK[v]}></span>
					<span class="flex-1">{VERDICT_LABELS[v]}</span>
					<span class="text-muted">{verdictCounts[v]}</span>
				</label>
			{/each}
		</fieldset>

		<fieldset class="mt-5">
			<legend class="rail-title">Stage</legend>
			{#each stageCounts as [stage, n] (stage)}
				<label class="rail-row">
					<input
						type="checkbox"
						checked={!hidden.stage.includes(stage)}
						onchange={() => toggle('stage', stage)}
					/>
					<span class="flex-1">{stage}</span>
					<span class="text-muted">{n}</span>
				</label>
			{/each}
		</fieldset>

		<fieldset class="mt-5">
			<legend class="rail-title">Business unit</legend>
			{#each buCounts as [bu, n] (bu)}
				<label class="rail-row">
					<input
						type="checkbox"
						checked={!hidden.bu.includes(bu)}
						onchange={() => toggle('bu', bu)}
					/>
					<span class="flex-1">{bu}</span>
					<span class="text-muted">{n}</span>
				</label>
			{/each}
		</fieldset>

		<fieldset class="mt-5">
			<legend class="rail-title">Purpose</legend>
			{#each modeCounts as [mode, n] (mode)}
				<label class="rail-row">
					<input
						type="checkbox"
						checked={!hidden.mode.includes(mode)}
						onchange={() => toggle('mode', mode)}
					/>
					<span class="flex-1">{MODE_LABELS[mode as Mode]}</span>
					<span class="text-muted">{n}</span>
				</label>
			{/each}
		</fieldset>

		<label class="mt-5 block">
			<span class="rail-title block">Owner</span>
			<select bind:value={owner} class="field mt-1 w-full">
				<option value="">All owners</option>
				{#each owners as o (o.id)}<option value={o.id}>{o.name}</option>{/each}
			</select>
		</label>

		<div class="mt-5 border-t border-line pt-4">
			<label class="rail-row">
				<input type="checkbox" checked={mine} onchange={(e) => setMine(e.currentTarget.checked)} />
				<span>Only my projects</span>
			</label>
			<label class="rail-row">
				<input type="checkbox" bind:checked={archivedOnly} />
				<span>Archived projects</span>
			</label>
		</div>

		<section class="mt-5 border-t border-line pt-4" aria-labelledby="stuck-title">
			<h2 id="stuck-title" class="rail-title">Where projects get stuck</h2>
			{#if stuck.length === 0}
				<p class="text-sm text-muted">No answers yet.</p>
			{/if}
			<ul class="space-y-2">
				{#each stuck as s (s.id)}
					<li class="grid grid-cols-[5.5rem_1fr_1.5rem] items-center gap-2 text-sm">
						<span>{DIM_SHORT[s.id]}</span>
						<span class="h-2 bg-[#DCE0E5]"
							><span class="block h-2 bg-ink" style:width="{(s.n / stuckMax) * 100}%"></span></span
						>
						<span class="text-right font-mono text-xs">{s.n}</span>
					</li>
				{/each}
			</ul>
			<p class="mt-2 text-xs text-muted">Projects whose weakest link is in each dimension.</p>
		</section>
	</aside>

	<!-- Table -->
	<main class="min-w-0 flex-1">
		<div
			class="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel px-4 py-3 sm:px-5"
		>
			<h2 class="font-semibold">
				AI project portfolio
				<span class="ml-2 text-sm font-normal text-muted"
					>{visible.length} of {projects.length} projects · weakest first</span
				>
			</h2>
			<div class="flex flex-wrap gap-2">
				<button
					type="button"
					class="btn"
					aria-expanded={showSummary}
					onclick={() => (showSummary = !showSummary)}>AI portfolio summary</button
				>
				{#if canExport}
					<details class="export relative">
						<summary class="btn list-none">Export</summary>
						<div
							class="absolute right-0 z-20 mt-1 flex w-56 flex-col border border-line bg-panel py-1 shadow-md"
						>
							<!-- eslint-disable svelte/no-navigation-without-resolve -- server files, not pages -->
							<a href="/api/export.xlsx" download class="export-item"
								>Excel (.xlsx)<span>Answers and Portfolio sheets</span></a
							>
							<a href="/api/export.csv" download class="export-item"
								>CSV<span>One row per project and question</span></a
							>
							<!-- eslint-enable svelte/no-navigation-without-resolve -->
						</div>
					</details>
				{/if}
				{#if canCreate}
					<a href={resolve('/projects/new')} class="btn-primary">New project</a>
				{/if}
			</div>
		</div>

		{#if showSummary}
			<div class="px-4 pt-4 sm:px-5">
				<SummaryPanel onclose={() => (showSummary = false)} />
			</div>
		{/if}

		{#if error}
			<p role="alert" class="m-5 border-l-4 border-weak bg-panel p-4">{error}</p>
		{:else if !loaded}
			<p class="p-5 text-muted">Loading projects…</p>
		{:else if visible.length === 0}
			<p class="p-5 text-muted">No projects match these filters.</p>
		{:else}
			<div class="overflow-x-auto p-4 sm:p-5">
				<table class="w-full min-w-[1080px] border border-line bg-panel text-sm">
					<thead>
						<tr
							class="border-b border-ink text-left text-xs tracking-[0.06em] text-muted uppercase"
						>
							<th scope="col" class="px-3 py-2 font-semibold">Project</th>
							<th scope="col" class="px-2 py-2 font-semibold">Stage</th>
							{#each DIMENSION_IDS as d (d)}
								<th scope="col" class="w-11 px-0.5 py-2 text-center font-semibold">
									<abbr title={DIM_SHORT[d]} class="no-underline">{DIM_ABBR[d]}</abbr>
								</th>
							{/each}
							<th scope="col" class="px-3 py-2 font-semibold">Weakest link</th>
							<th scope="col" class="px-2 py-2 font-semibold">Verdict</th>
							<th scope="col" class="px-2 py-2 font-semibold">Answered</th>
							<th scope="col" class="px-3 py-2 font-semibold">Owner</th>
						</tr>
					</thead>
					<tbody>
						{#each visible as p (p.id)}
							<tr class="border-b border-[#E1E5EA] last:border-0 hover:bg-[#F7F8F9]">
								<td class="px-3 py-2">
									<a
										href={resolve(`/projects/${p.id}`)}
										class="font-medium text-ink underline-offset-4 hover:text-teal hover:underline"
										>{p.name}</a
									>
									<span class="block text-xs text-muted"
										>{p.business_unit || 'No business unit'} · {p.mode === 'plan'
											? 'Planning'
											: 'Assessing'}</span
									>
								</td>
								<td class="px-2 py-2 whitespace-nowrap">{p.stage}</td>
								{#each p.score.dimensions as dim (dim.id)}
									<td class="px-0.5 py-1">
										<ScoreCell {dim} weakest={p.score.weakest.includes(dim.id)} />
									</td>
								{/each}
								<td class="px-3 py-2 font-mono text-xs">{weakText(p)}</td>
								<td class="px-2 py-2"><VerdictMark score={p.score} /></td>
								<td class="px-2 py-2">
									<span class="font-mono text-xs">{p.score.answered}/40</span>
									<span class="mt-1 block h-1 w-16 bg-[#E1E5EA]"
										><span class="block h-1 bg-teal" style:width="{p.score.coverage * 100}%"
										></span></span
									>
								</td>
								<td class="px-3 py-2 whitespace-nowrap">{p.owner?.name ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}

		<p class="border-t border-line px-4 py-3 font-mono text-xs text-muted sm:px-5">
			Yes 5 · Partly 3 · No 1 · Don't know 1 · any No caps the dimension at 3.0 · the weakest
			dimension decides
		</p>
	</main>
</div>

<style>
	.rail-title {
		margin-bottom: 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--color-muted);
	}
	.rail-row {
		display: flex;
		min-height: 2.25rem;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.9rem;
		cursor: pointer;
	}
	.export summary::-webkit-details-marker {
		display: none;
	}
	.export-item {
		display: flex;
		min-height: 2.75rem;
		flex-direction: column;
		justify-content: center;
		padding: 0.25rem 0.875rem;
		font-size: 0.9rem;
		color: var(--color-ink);
		text-decoration: none;
	}
	.export-item:hover {
		background: var(--color-canvas);
	}
	.export-item span {
		font-size: 0.75rem;
		color: var(--color-muted);
	}
	.rail-row input {
		width: 1.1rem;
		height: 1.1rem;
		accent-color: var(--color-ink);
	}
</style>
