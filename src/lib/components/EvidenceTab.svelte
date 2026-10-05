<script lang="ts">
	import { onMount } from 'svelte';
	import {
		api,
		type AcceptAllOut,
		type AnswerSaved,
		type Dimension,
		type EvidenceOut,
		type Suggestion,
		type SuggestionDone
	} from '$lib/api';

	let {
		projectId,
		dims,
		onsaved,
		onacceptall,
		onfocus
	}: {
		projectId: string;
		dims: Dimension[];
		onsaved: (saved: AnswerSaved) => void;
		onacceptall: (res: AcceptAllOut) => void;
		onfocus: (questionId: string) => void;
	} = $props();

	let text = $state('');
	let files = $state<FileList | null>(null);
	let fileInput = $state<HTMLInputElement>();
	let busy = $state(false);
	let message = $state('');
	let error = $state('');
	let suggestions = $state<Suggestion[]>([]);

	const questionText = $derived(
		Object.fromEntries(dims.flatMap((d) => d.questions.map((q) => [q.id, q.text])))
	);

	onMount(async () => {
		try {
			suggestions = await api<Suggestion[]>(`/projects/${projectId}/suggestions`);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});

	async function read() {
		const file = files?.[0];
		if (!text.trim() && !file) {
			error = 'Paste some text or choose a file first.';
			return;
		}
		busy = true;
		error = '';
		message = '';
		const form = new FormData();
		form.append('text', text);
		if (file) form.append('file', file);
		try {
			const res = await api<EvidenceOut>(`/projects/${projectId}/agent/evidence`, {
				method: 'POST',
				body: form
			});
			const n = res.suggestions.length;
			message =
				(n === 0
					? `No new answers found in ${res.filename}.`
					: `Found ${n} possible answer${n === 1 ? '' : 's'} in ${res.filename}. Check each one.`) +
				(res.truncated
					? ` The text was long, so only the first ${res.chars_read.toLocaleString('en-GB')} characters were read.`
					: '');
			suggestions = await api<Suggestion[]>(`/projects/${projectId}/suggestions`);
			text = '';
			files = null;
			if (fileInput) fileInput.value = '';
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	async function decide(s: Suggestion, action: 'accept' | 'dismiss') {
		error = '';
		try {
			const res = await api<SuggestionDone>(`/suggestions/${s.id}/${action}`, { method: 'POST' });
			if (res.saved) onsaved(res.saved);
			suggestions = suggestions.filter((x) => x.id !== s.id);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	async function acceptAll() {
		error = '';
		try {
			const res = await api<AcceptAllOut>(`/projects/${projectId}/suggestions/accept-all`, {
				method: 'POST'
			});
			onacceptall(res);
			suggestions = [];
			message = `Accepted ${res.accepted} answer${res.accepted === 1 ? '' : 's'}.`;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	const PILL = {
		Yes: 'bg-[#1F7A4C] text-white',
		Partly: 'bg-partial text-[#2B1C00]',
		No: 'bg-weak text-white'
	};
</script>

<div class="h-full overflow-y-auto p-4">
	<label for="evidence-text" class="label">Paste text from a plan, report or meeting notes</label>
	<textarea
		id="evidence-text"
		class="field w-full resize-y"
		rows="5"
		bind:value={text}
		disabled={busy}></textarea>

	<label for="evidence-file" class="label mt-3">Or choose a file</label>
	<input
		id="evidence-file"
		bind:this={fileInput}
		type="file"
		accept=".txt,.md,.csv,.docx,.pdf"
		bind:files
		disabled={busy}
		class="block w-full text-sm file:mr-3 file:min-h-11 file:border file:border-line file:bg-white file:px-3 file:text-sm"
	/>
	<p class="mt-1 text-xs text-muted">
		txt, md, csv, docx or pdf, up to 10 MB. We keep the text in our database. The AI reads at most
		the first 24,000 characters.
	</p>

	<button type="button" class="btn-primary mt-3 w-full" onclick={read} disabled={busy}>
		{busy ? 'Reading…' : 'Read evidence'}
	</button>

	<div aria-live="polite">
		{#if error}<p role="alert" class="mt-3 text-sm text-weak">{error}</p>{/if}
		{#if message}<p class="mt-3 text-sm">{message}</p>{/if}
	</div>

	{#if suggestions.length}
		<section class="mt-5" aria-labelledby="suggestions-title">
			<div class="flex items-center justify-between gap-2 border-b border-line pb-2">
				<h3 id="suggestions-title" class="font-semibold">
					Suggested answers <span class="font-normal text-muted">({suggestions.length})</span>
				</h3>
				<button type="button" class="btn min-h-9" onclick={acceptAll}>Accept all</button>
			</div>
			<ul class="divide-y divide-[#E1E5EA]">
				{#each suggestions as s (s.id)}
					<li class="py-3">
						<p class="text-sm">
							<button
								type="button"
								class="font-mono font-semibold text-teal underline-offset-4 hover:underline"
								onclick={() => onfocus(s.question_id)}>{s.question_id}</button
							>
							{questionText[s.question_id] ?? ''}
						</p>
						<p class="mt-2 flex items-start gap-2 text-sm">
							<span class="shrink-0 px-2 py-0.5 text-xs font-semibold {PILL[s.answer]}"
								>{s.answer}</span
							>
							<span>{s.evidence}</span>
						</p>
						<p class="mt-1 font-mono text-[11px] text-muted">
							AI SUGGESTED · from {s.source_excerpt}
						</p>
						<div class="mt-2 flex gap-2">
							<button type="button" class="btn min-h-9" onclick={() => decide(s, 'accept')}
								>Accept</button
							>
							<button type="button" class="btn min-h-9" onclick={() => decide(s, 'dismiss')}
								>Dismiss</button
							>
						</div>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>
