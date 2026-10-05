<script lang="ts">
	import { ANSWER_LABELS, type AnswerValue, type HistoryRow } from '$lib/api';
	import { formatDateTime } from '$lib/text';

	let {
		rows,
		questionId = null,
		onclear
	}: { rows: HistoryRow[]; questionId?: string | null; onclear: () => void } = $props();

	const SOURCE = {
		person: '',
		ai_interview: 'AI interview',
		ai_evidence: 'AI from evidence',
		confirm: 'Confirmed',
		undo: 'Undone'
	};
	const label = (v: AnswerValue | null) => (v ? ANSWER_LABELS[v] : 'blank');
	const shown = $derived(questionId ? rows.filter((r) => r.question_id === questionId) : rows);
</script>

<section aria-labelledby="history-title" class="flex h-full flex-col">
	<div class="flex items-center justify-between border-b border-line px-4 py-3">
		<h2 id="history-title" class="font-semibold">
			{questionId ? `Changes to ${questionId}` : 'Changes'}
		</h2>
		{#if questionId}
			<button type="button" class="min-h-11 text-sm text-teal underline" onclick={onclear}
				>Show all</button
			>
		{/if}
	</div>
	{#if shown.length === 0}
		<p class="p-4 text-sm text-muted">No changes yet.</p>
	{:else}
		<ol class="divide-y divide-divider overflow-y-auto">
			{#each shown as h (h.id)}
				<li class="px-4 py-3 text-sm">
					<p>
						<span class="font-mono font-semibold">{h.question_id}</span>
						{#if h.source === 'confirm'}
							· {label(h.new_answer)} confirmed
						{:else if h.old_answer !== h.new_answer}
							· {label(h.old_answer)} → <strong>{label(h.new_answer)}</strong>
						{:else}
							· evidence changed
						{/if}
						{#if SOURCE[h.source] && h.source !== 'confirm'}
							<span class="ml-1 bg-ai-bg px-1 font-mono text-[11px] text-ai-ink"
								>{SOURCE[h.source]}</span
							>
						{/if}
					</p>
					{#if h.new_evidence && h.new_evidence !== h.old_evidence}
						<p class="mt-1 text-muted">“{h.new_evidence}”</p>
					{/if}
					<p class="mt-1 text-xs text-muted">
						{h.changed_by?.name ?? 'Unknown'} · {formatDateTime(h.changed_at)}
					</p>
				</li>
			{/each}
		</ol>
	{/if}
</section>
