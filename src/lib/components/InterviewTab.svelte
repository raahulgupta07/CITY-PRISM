<script lang="ts">
	import { tick } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import {
		api,
		ANSWER_LABELS,
		type AnswerRow,
		type AnswerSaved,
		type Dimension,
		type InterviewOut,
		type Question
	} from '$lib/api';
	import { nextQuestion } from '$lib/interview';

	let {
		projectId,
		dims,
		answers,
		current,
		onsaved,
		onfocus
	}: {
		projectId: string;
		dims: Dimension[];
		answers: Record<string, AnswerRow>;
		current: number;
		onsaved: (saved: AnswerSaved) => void;
		onfocus: (questionId: string) => void;
	} = $props();

	type Entry =
		| { kind: 'agent'; qid: string; text: string }
		| { kind: 'you'; text: string }
		| { kind: 'recorded'; qid: string; text: string; undone: boolean }
		| { kind: 'note'; text: string; error?: boolean };

	let log = $state<Entry[]>([]);
	let active = $state<Question | null>(null);
	let context = $state(''); // earlier vague replies to the active question
	let reply = $state('');
	let busy = $state(false);
	let running = $state(false);
	const skipped = new SvelteSet<string>();
	let logEl = $state<HTMLOListElement>();
	let inputEl = $state<HTMLTextAreaElement>();

	const lastRecorded = $derived(log.findLastIndex((e) => e.kind === 'recorded' && !e.undone));

	async function push(entry: Entry) {
		log.push(entry);
		await tick();
		logEl?.scrollTo({ top: logEl.scrollHeight });
	}

	function ask() {
		const q = nextQuestion(dims, answers, current, skipped);
		active = q;
		context = '';
		if (!q) {
			running = false;
			push({ kind: 'note', text: 'Every question is answered or skipped.' });
			return;
		}
		onfocus(q.id);
		push({ kind: 'agent', qid: q.id, text: q.text });
		inputEl?.focus();
	}

	function start() {
		running = true;
		skipped.clear();
		ask();
	}

	function stop() {
		running = false;
		active = null;
		push({ kind: 'note', text: 'Interview stopped. Your answers are saved.' });
	}

	function skip() {
		if (!active) return;
		skipped.add(active.id);
		push({ kind: 'note', text: `Skipped ${active.id}.` });
		ask();
	}

	async function send() {
		const text = reply.trim();
		if (!active || !text || busy) return;
		const q = active;
		busy = true;
		push({ kind: 'you', text });
		reply = '';
		try {
			const res = await api<InterviewOut>(`/projects/${projectId}/agent/interview`, {
				method: 'POST',
				body: JSON.stringify({ question_id: q.id, reply: text, context })
			});
			if (res.saved) {
				onsaved(res.saved);
				const label = ANSWER_LABELS[res.saved.answer.answer!];
				await push({
					kind: 'recorded',
					qid: q.id,
					text: `${label}. ${res.evidence}`,
					undone: false
				});
				ask();
			} else {
				context = context ? `${context} ${text}` : text;
				push({ kind: 'agent', qid: q.id, text: res.followUp });
			}
		} catch (e) {
			reply = text; // keep what they typed
			push({ kind: 'note', text: e instanceof Error ? e.message : String(e), error: true });
		} finally {
			busy = false;
			inputEl?.focus();
		}
	}

	async function undo(index: number) {
		const entry = log[index];
		if (entry.kind !== 'recorded' || busy) return;
		busy = true;
		try {
			const res = await api<AnswerSaved>(`/projects/${projectId}/answers/${entry.qid}/undo`, {
				method: 'POST'
			});
			onsaved(res);
			entry.undone = true;
			const now = res.answer.answer
				? `is back to ${ANSWER_LABELS[res.answer.answer]}`
				: 'is blank again';
			push({
				kind: 'note',
				text: `Undone. ${entry.qid} ${now}. The change stays in the history.`
			});
		} catch (e) {
			push({ kind: 'note', text: e instanceof Error ? e.message : String(e), error: true });
		} finally {
			busy = false;
		}
	}

	function keydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
			e.preventDefault();
			send();
		}
	}
</script>

<div class="flex h-full min-h-0 flex-col">
	<ol
		bind:this={logEl}
		class="min-h-40 flex-1 space-y-4 overflow-y-auto p-4"
		aria-live="polite"
		aria-label="Interview"
	>
		{#if log.length === 0}
			<li class="text-sm text-muted">
				The agent asks the open questions one by one, starting with this dimension. Answer in your
				own words. The agent records Yes, Partly, No or Don't know, and you can undo it.
			</li>
		{/if}
		{#each log as entry, i (i)}
			<li>
				{#if entry.kind === 'agent'}
					<p class="font-mono text-[11px] tracking-[0.06em] text-muted">AGENT · {entry.qid}</p>
					<p class="mt-1 text-[15px]">{entry.text}</p>
				{:else if entry.kind === 'you'}
					<div class="border-l-2 border-ink pl-3">
						<p class="font-mono text-[11px] tracking-[0.06em] text-muted">YOU</p>
						<p class="mt-1 text-[15px] whitespace-pre-wrap">{entry.text}</p>
					</div>
				{:else if entry.kind === 'recorded'}
					<div class="bg-ai-bg p-3 text-ai-ink" class:opacity-60={entry.undone}>
						<div class="flex items-center justify-between gap-2">
							<p class="font-mono text-xs font-semibold tracking-[0.04em]">
								RECORDED {entry.qid}{entry.undone ? ' · UNDONE' : ''}
							</p>
							{#if i === lastRecorded}
								<button
									type="button"
									class="min-h-11 border border-ai-ink bg-panel px-3 text-sm font-semibold"
									disabled={busy}
									onclick={() => undo(i)}>Undo</button
								>
							{/if}
						</div>
						<p class="mt-1 text-sm">{entry.text}</p>
					</div>
				{:else}
					<p class="text-sm {entry.error ? 'text-danger' : 'text-muted'}">{entry.text}</p>
				{/if}
			</li>
		{/each}
	</ol>

	<div class="border-t border-line p-4">
		{#if running && active}
			<label for="interview-reply" class="text-sm text-muted">Answer in your own words</label>
			<textarea
				id="interview-reply"
				bind:this={inputEl}
				bind:value={reply}
				onkeydown={keydown}
				maxlength="2000"
				rows="3"
				aria-describedby="interview-hint"
				class="field mt-1 w-full resize-y"
				disabled={busy}></textarea>
			<p id="interview-hint" class="mt-1 text-xs text-muted">Ctrl+Enter also sends.</p>
			<div class="mt-2 flex flex-wrap gap-2">
				<button type="button" class="btn" onclick={skip} disabled={busy}>Skip</button>
				<button type="button" class="btn" onclick={stop} disabled={busy}>Stop</button>
				<button
					type="button"
					class="btn-primary ml-auto"
					onclick={send}
					disabled={busy || !reply.trim()}>{busy ? 'Thinking…' : 'Send'}</button
				>
			</div>
		{:else}
			<button type="button" class="btn-primary w-full" onclick={start}>
				{log.length ? 'Start again' : 'Start interview'}
			</button>
		{/if}
	</div>
</div>
