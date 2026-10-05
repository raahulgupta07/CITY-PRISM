<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import {
		api,
		MODE_LABELS,
		STAGES,
		type AcceptAllOut,
		type AnswerRow,
		type AnswerSaved,
		type AnswerValue,
		type Dimension,
		type HistoryRow,
		type ProjectDetail,
		type Score,
		type Stage
	} from '$lib/api';
	import { BAND_ON_DARK as DARK, faded } from '$lib/colours';
	import EvidenceTab from '$lib/components/EvidenceTab.svelte';
	import HistoryPanel from '$lib/components/HistoryPanel.svelte';
	import InterviewTab from '$lib/components/InterviewTab.svelte';
	import QuestionRow from '$lib/components/QuestionRow.svelte';
	import VerdictMark from '$lib/components/VerdictMark.svelte';
	import { scoreProject } from '$lib/scoring';
	import { session } from '$lib/session.svelte';
	import { tabKeys } from '$lib/tabs';
	import { DIM_SHORT, formatDate, formatScore, projectSentence } from '$lib/text';

	const id = $derived(page.params.id ?? '');

	let project = $state<ProjectDetail | null>(null);
	let dims = $state<Dimension[]>([]);
	let answers = $state<Record<string, AnswerRow>>({});
	let score = $state<Score | null>(null);
	let history = $state<HistoryRow[]>([]);
	let historyFor = $state<string | null>(null);
	let agentTab = $state<'interview' | 'evidence' | 'changes'>('interview');
	let current = $state(1);
	let status = $state<Record<string, string>>({});
	let error = $state('');
	let notice = $state('');

	// Not reactive on purpose: only used to chain saves.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const queues = new Map<string, Promise<unknown>>();

	$effect(() => {
		const pid = id;
		error = '';
		project = null;
		Promise.all([api<ProjectDetail>(`/projects/${pid}`), api<Dimension[]>('/questions')])
			.then(([p, d]) => {
				project = p;
				dims = d;
				answers = Object.fromEntries(p.answers.map((a) => [a.question_id, a]));
				score = p.score;
				// Open on the weakest dimension, else the first.
				current = p.score.weakest[0] ?? d[0]?.id ?? 1;
				loadHistory();
			})
			.catch((e) => (error = e instanceof Error ? e.message : String(e)));
	});

	async function loadHistory() {
		try {
			history = await api<HistoryRow[]>(`/projects/${id}/history`);
		} catch {
			// The history panel is secondary; the answers still work.
		}
	}

	const canEdit = $derived(!!project?.can_edit && !project.archived);
	const canArchive = $derived(session.user?.role === 'reviewer' || session.user?.role === 'admin');
	const dim = $derived(dims.find((d) => d.id === current));
	const dimScore = $derived(score?.dimensions.find((d) => d.id === current));

	function localScore(): Score {
		return scoreProject(
			Object.fromEntries(Object.values(answers).map((a) => [a.question_id, a.answer]))
		);
	}

	/** Save one answer. The score updates at once; the server result replaces it. */
	/** Apply an answer saved by the agent (interview, undo, accepted suggestion). */
	function applySaved(res: AnswerSaved) {
		answers[res.answer.question_id] = res.answer;
		score = res.score;
		if (res.changed) loadHistory();
	}

	function applyAcceptAll(res: AcceptAllOut) {
		for (const a of res.answers) answers[a.question_id] = a;
		score = res.score;
		loadHistory();
	}

	/** Show the dimension that holds this question. */
	function focusQuestion(qid: string) {
		const dimId = Number(qid.split('.')[0]);
		if (dimId) current = dimId;
	}

	function save(qid: string, answer: AnswerValue | null, evidence: string) {
		const before = answers[qid];
		answers[qid] = {
			question_id: qid,
			answer,
			evidence: evidence.trim(),
			source: 'person',
			confirmed: true,
			updated_by: before?.updated_by ?? null,
			updated_at: before?.updated_at ?? new Date().toISOString()
		};
		score = localScore();
		status[qid] = 'Saving…';
		run(
			qid,
			() =>
				api<AnswerSaved>(`/projects/${id}/answers/${qid}`, {
					method: 'PUT',
					body: JSON.stringify({ answer, evidence })
				}),
			before
		);
	}

	function confirmAnswer(qid: string) {
		status[qid] = 'Saving…';
		run(
			qid,
			() => api<AnswerSaved>(`/projects/${id}/answers/${qid}/confirm`, { method: 'POST' }),
			answers[qid]
		);
	}

	/** One save at a time per question, so answers never arrive out of order. */
	function run(qid: string, call: () => Promise<AnswerSaved>, before: AnswerRow | undefined) {
		const next = (queues.get(qid) ?? Promise.resolve())
			.then(call)
			.then((res) => {
				answers[qid] = res.answer;
				score = res.score;
				status[qid] = 'Saved';
				if (res.changed) loadHistory();
			})
			.catch((e) => {
				if (before) answers[qid] = before;
				else delete answers[qid];
				score = localScore();
				status[qid] = `Could not save: ${e instanceof Error ? e.message : String(e)}`;
			});
		queues.set(qid, next);
	}

	async function patch(body: Record<string, unknown>, message: string) {
		try {
			const p = await api<ProjectDetail>(`/projects/${id}`, {
				method: 'PATCH',
				body: JSON.stringify(body)
			});
			project = p;
			notice = message;
		} catch (e) {
			notice = `Could not save: ${e instanceof Error ? e.message : String(e)}`;
		}
	}

	function setArchived(archived: boolean) {
		if (
			archived &&
			!confirm('Archive this project? It will be hidden from the portfolio. Nothing is deleted.')
		)
			return;
		patch({ archived }, archived ? 'Project archived.' : 'Project restored.');
	}

	// On phones the tabs scroll sideways; keep the current one in view.
	// Only the tab row scrolls, never the page.
	$effect(() => {
		const tab = document.getElementById(`tab-${current}`);
		const row = tab?.parentElement;
		if (!tab || !row || row.scrollWidth <= row.clientWidth) return;
		row.scrollTo({ left: tab.offsetLeft - (row.clientWidth - tab.offsetWidth) / 2 });
	});

	// Arrow keys move between dimension tabs.
	function tabKey(e: KeyboardEvent) {
		tabKeys(
			e,
			dims.map((d) => d.id),
			current,
			(k) => (current = k),
			'tab-'
		);
	}

	const AGENT_TABS = [
		['interview', 'Interview'],
		['evidence', 'Read evidence'],
		['changes', 'Changes']
	] as const;

	const BAND_BOX = {
		weak: 'bg-weak text-white',
		partial: 'bg-partial text-on-partial',
		strong: 'bg-strong text-white',
		none: 'bg-none-bg text-none-ink'
	};
</script>

<svelte:head><title>{project ? `${project.name} · ` : ''}Assess · City Prism</title></svelte:head>

{#if error}
	<main class="p-6">
		<p role="alert" class="border-l-4 border-weak bg-panel p-4">{error}</p>
		<a href={resolve('/')} class="mt-4 inline-block text-teal underline">Back to the portfolio</a>
	</main>
{:else if !project || !score}
	<p class="p-6 text-muted">Loading project…</p>
{:else}
	<!-- Dark band: project facts, rules sentence, dimension bars as tabs -->
	<section class="band bg-navy px-4 pt-5 text-band-ink sm:px-7">
		<nav aria-label="Breadcrumb" class="text-sm text-band-muted">
			<a href={resolve('/')} class="text-band-muted underline-offset-4 hover:underline">Portfolio</a
			>
			/ <span class="text-white">{project.name}</span>
		</nav>
		<div class="mt-3 flex flex-wrap items-start justify-between gap-6">
			<div class="max-w-3xl">
				<p class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-band-muted">
					<span>{project.business_unit || 'No business unit'}</span>
					{#if project.sponsor}<span>Sponsor: {project.sponsor}</span>{/if}
					<span>Owner: {project.owner?.name ?? 'Not set'}</span>
					<span>{MODE_LABELS[project.mode]}</span>
					{#if project.due_date}<span>Due {formatDate(project.due_date)}</span>{/if}
					<label class="flex items-center gap-2">
						Stage
						{#if canEdit}
							<select
								class="min-h-11 border border-band-line bg-band-raised px-2 text-white"
								value={project.stage}
								onchange={(e) => patch({ stage: e.currentTarget.value as Stage }, 'Stage saved.')}
							>
								{#each STAGES as s (s)}<option value={s}>{s}</option>{/each}
							</select>
						{:else}
							<span class="text-white">{project.stage}</span>
						{/if}
					</label>
				</p>
				<h1 class="mt-3 font-condensed text-3xl font-medium text-white sm:text-4xl">
					{project.name}
				</h1>
				<p class="mt-2 text-[17px] text-band-soft" aria-live="polite">{projectSentence(score)}</p>
			</div>
			<div class="w-full max-w-60">
				<p class="flex justify-between text-sm text-band-muted">
					Answered <span class="font-mono text-white">{score.answered}/40</span>
				</p>
				<div class="mt-1 h-1 bg-band-line">
					<div class="h-1 bg-teal-on-dark" style:width="{score.coverage * 100}%"></div>
				</div>
				<p class="mt-3 text-sm"><VerdictMark {score} dark /></p>
				<a href={resolve(`/projects/${project.id}/brief`)} class="btn-primary mt-3 w-full"
					>Decision brief →</a
				>
				{#if canArchive}
					<button
						type="button"
						class="mt-3 min-h-11 text-sm text-teal-on-dark underline underline-offset-4"
						onclick={() => setArchived(!project?.archived)}
						>{project.archived ? 'Restore project' : 'Archive project'}</button
					>
				{/if}
			</div>
		</div>

		<div
			role="tablist"
			aria-label="Dimensions"
			tabindex="-1"
			class="relative -mx-4 mt-5 flex gap-1 overflow-x-auto px-4 pb-3 sm:mx-0 sm:grid sm:grid-cols-8 sm:gap-0 sm:overflow-visible sm:px-0 sm:pb-0"
			onkeydown={tabKey}
		>
			{#each score.dimensions as d (d.id)}
				{@const on = d.id === current}
				{@const weak = score.weakest.includes(d.id)}
				<button
					type="button"
					role="tab"
					id="tab-{d.id}"
					aria-selected={on}
					aria-controls="dimension-panel"
					tabindex={on ? 0 : -1}
					class="flex min-h-11 shrink-0 flex-col justify-end gap-1 border px-3 py-2 text-left sm:gap-1.5 sm:border-0 sm:px-2.5 sm:pt-2 sm:pb-3 {on
						? 'border-teal-on-dark bg-band-raised sm:shadow-[inset_0_-3px_0_var(--color-teal-on-dark)]'
						: 'border-band-line hover:bg-band-hover'}"
					onclick={() => (current = d.id)}
				>
					<!-- Bars from small tablets up; on phones each tab is a chip. -->
					<span class="hidden h-11 items-end sm:flex">
						<span
							class="block w-full"
							style:height={d.score === null ? '2px' : `${Math.round((d.score / 5) * 44)}px`}
							style:background={d.score === null || weak ? DARK[d.band] : faded(DARK[d.band])}
							style:box-shadow={weak
								? `0 0 0 2px var(--color-navy), 0 0 0 3px ${DARK[d.band]}`
								: ''}
						></span>
					</span>
					<span class="flex items-center gap-2 sm:items-baseline">
						<span
							aria-hidden="true"
							class="size-2.5 shrink-0 sm:hidden"
							style:background={DARK[d.band]}
						></span>
						<span class="font-mono text-base text-white">{formatScore(d.score)}</span>
						<span class="font-mono text-[11px] text-band-muted">{d.answered}/5</span>
					</span>
					<span class="text-xs whitespace-nowrap text-band-soft"
						>{d.id}
						{DIM_SHORT[d.id]}{#if d.has_no}<span class="sr-only">, has a No</span
							>{/if}{#if weak}<span class="sr-only">, weakest link</span>{/if}</span
					>
				</button>
			{/each}
		</div>
	</section>

	{#if notice}
		<p role="status" class="border-b border-line bg-panel px-4 py-2 text-sm sm:px-7">{notice}</p>
	{/if}
	{#if project.archived}
		<p class="border-b border-line bg-warn-bg px-4 py-2 text-sm sm:px-7">
			This project is archived. Its answers are kept but cannot be changed.
		</p>
	{:else if !project.can_edit}
		<p class="border-b border-line bg-panel px-4 py-2 text-sm text-muted sm:px-7">
			You can read this project. Only its owner, reviewers and admins can change it.
		</p>
	{/if}

	<div class="grid lg:grid-cols-[1fr_22rem]">
		<main class="min-w-0">
			<div
				id="dimension-panel"
				role="tabpanel"
				aria-labelledby="tab-{current}"
				class="space-y-4 p-4 sm:p-6"
			>
				{#if dim && dimScore}
					<section
						class="flex flex-wrap items-start justify-between gap-4 border border-line bg-panel p-5"
					>
						<div class="max-w-2xl">
							<p class="text-xs font-semibold tracking-[0.08em] text-muted uppercase">
								Dimension {dim.id} · {dim.group_name}
							</p>
							<h2 class="mt-1 text-xl font-semibold">{dim.title}</h2>
							<p class="mt-1 text-[15px]">{dim.lead_question}</p>
							{#if dim.questions.some((q) => q.is_draft)}
								<p class="mt-2 text-sm text-muted">
									Draft wording: the City AI team may still change these questions.
								</p>
							{/if}
						</div>
						<div class="text-right">
							<p
								class="inline-block px-3.5 py-2 font-mono text-3xl leading-none {BAND_BOX[
									dimScore.band
								]}"
							>
								{formatScore(dimScore.score)}
							</p>
							<p class="mt-1 text-sm text-muted">
								{#if dimScore.score === null}
									No answers yet
								{:else if dimScore.capped}
									Capped at 3.0 because of a No (raw {formatScore(dimScore.raw)})
								{:else}
									Average of {dimScore.answered} answer{dimScore.answered === 1 ? '' : 's'}
								{/if}
							</p>
						</div>
					</section>

					{#each dim.questions.filter((q) => q.active) as q (q.id)}
						<QuestionRow
							question={q}
							row={answers[q.id]}
							{canEdit}
							status={status[q.id] ?? ''}
							onanswer={(v, evidence) => save(q.id, v, evidence)}
							onevidence={(evidence) => save(q.id, answers[q.id]?.answer ?? null, evidence)}
							onconfirm={() => confirmAnswer(q.id)}
							onhistory={() => {
								historyFor = q.id;
								agentTab = 'changes';
							}}
						/>
					{/each}

					<div class="flex justify-between">
						{#if current > 1}
							<button type="button" class="btn" onclick={() => (current -= 1)}
								>← {DIM_SHORT[current - 1]}</button
							>
						{:else}<span></span>{/if}
						{#if current < 8}
							<button type="button" class="btn" onclick={() => (current += 1)}
								>{DIM_SHORT[current + 1]} →</button
							>
						{/if}
					</div>
				{/if}
			</div>
		</main>

		<aside
			class="flex flex-col border-t border-line bg-panel lg:sticky lg:top-0 lg:h-screen lg:border-t-0 lg:border-l"
			aria-label="Agent"
		>
			<div
				role="tablist"
				aria-label="Agent"
				tabindex="-1"
				class="grid shrink-0 grid-cols-3 border-b border-line"
				onkeydown={(e) =>
					tabKeys(
						e,
						AGENT_TABS.map(([k]) => k),
						agentTab,
						(k) => (agentTab = k),
						'agent-tab-'
					)}
			>
				{#each AGENT_TABS as [key, label] (key)}
					<button
						type="button"
						role="tab"
						id="agent-tab-{key}"
						aria-selected={agentTab === key}
						aria-controls="agent-panel"
						tabindex={agentTab === key ? 0 : -1}
						class="min-h-12 px-2 text-sm {agentTab === key
							? 'font-semibold shadow-[inset_0_-2px_0_var(--color-teal)]'
							: 'bg-subtle text-muted hover:text-ink'}"
						onclick={() => (agentTab = key)}>{label}</button
					>
				{/each}
			</div>
			<div
				id="agent-panel"
				role="tabpanel"
				aria-labelledby="agent-tab-{agentTab}"
				class="min-h-0 flex-1"
			>
				{#if agentTab === 'changes'}
					<HistoryPanel
						rows={history}
						questionId={historyFor}
						onclear={() => (historyFor = null)}
					/>
				{:else if !canEdit}
					<p class="p-4 text-sm text-muted">
						Only the project owner, reviewers and admins can use the agent on this project.
					</p>
				{:else}
					<!-- Both stay mounted so switching tabs keeps the conversation. -->
					<div class="h-full" hidden={agentTab !== 'interview'}>
						<InterviewTab
							projectId={id}
							{dims}
							{answers}
							{current}
							onsaved={applySaved}
							onfocus={focusQuestion}
						/>
					</div>
					<div class="h-full" hidden={agentTab !== 'evidence'}>
						<EvidenceTab
							projectId={id}
							{dims}
							onsaved={applySaved}
							onacceptall={applyAcceptAll}
							onfocus={focusQuestion}
						/>
					</div>
				{/if}
			</div>
		</aside>
	</div>
{/if}
