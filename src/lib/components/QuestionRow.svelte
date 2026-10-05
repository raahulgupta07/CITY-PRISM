<script lang="ts">
	import { EVIDENCE_MAX, type AnswerRow, type AnswerValue, type Question } from '$lib/api';
	import { formatDateTime } from '$lib/text';
	import AnswerControl from './AnswerControl.svelte';

	let {
		question,
		row,
		canEdit,
		status = '',
		onanswer,
		onevidence,
		onconfirm,
		onhistory
	}: {
		question: Question;
		row: AnswerRow | undefined;
		canEdit: boolean;
		status?: string;
		onanswer: (v: AnswerValue | null, evidence: string) => void;
		onevidence: (evidence: string) => void;
		onconfirm: () => void;
		onhistory: () => void;
	} = $props();

	// Local draft so typing is not lost while a save is running.
	let draft = $state('');
	let lastSynced = '';
	$effect(() => {
		const server = row?.evidence ?? '';
		if (server !== lastSynced) {
			draft = server;
			lastSynced = server;
		}
	});

	const aiUnconfirmed = $derived(!!row?.answer && !row.confirmed);
	const sourceText = $derived(
		row?.source === 'ai_interview' ? 'from the interview' : 'from the evidence you shared'
	);
	const id = $derived(`q-${question.id.replace('.', '-')}`);

	function blur() {
		if (draft.trim() !== (row?.evidence ?? '')) onevidence(draft);
	}
</script>

<article class="border border-line bg-panel" aria-labelledby="{id}-text">
	<div class="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between sm:p-5">
		<h3 id="{id}-text" class="flex gap-3 text-[15px] leading-6 font-normal">
			<span class="font-mono font-semibold text-teal">{question.id}</span>
			<span>
				{question.text}
				{#if question.is_draft}
					<span class="ml-1 border border-line px-1.5 py-0.5 font-mono text-[11px] text-muted"
						>Draft wording</span
					>
				{/if}
			</span>
		</h3>
		<div class="shrink-0">
			<AnswerControl
				value={row?.answer ?? null}
				label="Answer for {question.id}"
				disabled={!canEdit}
				{aiUnconfirmed}
				onpick={(v) => onanswer(v, draft)}
			/>
		</div>
	</div>

	{#if aiUnconfirmed}
		<div
			class="mx-4 flex flex-wrap items-center justify-between gap-3 bg-ai-bg px-3 py-2 sm:mx-5 sm:ml-14"
		>
			<p class="text-sm text-ai-ink">
				<span class="font-mono text-xs font-semibold tracking-[0.04em]"
					>AI SUGGESTED · NOT CONFIRMED</span
				>
				{sourceText}
			</p>
			{#if canEdit}
				<button
					type="button"
					class="min-h-9 border border-ai-ink bg-white px-3 text-sm font-semibold text-ai-ink"
					onclick={onconfirm}>Confirm</button
				>
			{/if}
		</div>
	{/if}

	<div class="px-4 pb-4 sm:px-5 sm:pl-14">
		{#if canEdit}
			<label for="{id}-evidence" class="mt-3 block text-sm text-muted">Evidence</label>
			<textarea
				id="{id}-evidence"
				class="field mt-1 min-h-16 w-full resize-y text-[15px]"
				maxlength={EVIDENCE_MAX}
				placeholder="What shows this? A short fact, name or date."
				bind:value={draft}
				onblur={blur}></textarea>
			<p class="mt-0.5 text-right font-mono text-[11px] text-muted">
				{draft.length}/{EVIDENCE_MAX}
			</p>
		{:else if row?.evidence}
			<p class="mt-3 text-sm text-muted">Evidence</p>
			<p class="mt-1 text-[15px]">{row.evidence}</p>
		{/if}
		<div
			class="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-[#E1E5EA] pt-2 text-sm text-muted"
		>
			<span>
				{#if row?.updated_by}
					Last changed by {row.updated_by.name} · {formatDateTime(row.updated_at)}
				{:else}
					Not answered
				{/if}
				<span aria-live="polite" class="ml-2 {status.startsWith('Could') ? 'text-weak' : ''}"
					>{status}</span
				>
			</span>
			<button
				type="button"
				class="min-h-9 text-teal underline underline-offset-4"
				onclick={onhistory}>History</button
			>
		</div>
	</div>
</article>
