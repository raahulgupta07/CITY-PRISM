<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { streamSummary } from '$lib/sse';

	let { onclose }: { onclose: () => void } = $props();

	let text = $state('');
	let phase = $state<'writing' | 'done' | 'stopped' | 'error'>('writing');
	let error = $state('');
	let copied = $state(false);
	let controller: AbortController | null = null;

	async function write() {
		controller?.abort();
		const own = new AbortController();
		controller = own;
		text = '';
		error = '';
		copied = false;
		phase = 'writing';
		try {
			await streamSummary((piece) => (text += piece), own.signal);
			phase = 'done';
		} catch (e) {
			if (own.signal.aborted) return; // Stop, or a newer request took over
			error = e instanceof Error ? e.message : String(e);
			phase = 'error';
		}
	}

	function stop() {
		controller?.abort();
		phase = 'stopped';
	}

	async function copy() {
		try {
			await navigator.clipboard.writeText(text);
			copied = true;
		} catch {
			error = 'Could not copy. Select the text and copy it by hand.';
		}
	}

	onMount(write);
	onDestroy(() => controller?.abort());
</script>

<section class="border border-line bg-ai-bg p-5 text-ai-ink" aria-labelledby="summary-title">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<h2 id="summary-title" class="font-mono text-xs font-semibold tracking-[0.06em]">
			AI PORTFOLIO SUMMARY · WRITTEN BY AI
		</h2>
		<div class="flex flex-wrap gap-2">
			{#if phase === 'writing'}
				<button type="button" class="btn min-h-9" onclick={stop}>Stop</button>
			{:else}
				<button type="button" class="btn min-h-9" onclick={copy} disabled={!text}
					>{copied ? 'Copied' : 'Copy'}</button
				>
				<button type="button" class="btn min-h-9" onclick={write}>Write again</button>
			{/if}
			<button type="button" class="btn min-h-9" onclick={onclose}>Close</button>
		</div>
	</div>
	<div aria-live="polite" aria-busy={phase === 'writing'}>
		{#if text}
			<p class="mt-3 max-w-4xl text-[16px] leading-relaxed whitespace-pre-wrap text-ink">
				{text}{#if phase === 'writing'}<span aria-hidden="true" class="cursor">▍</span>{/if}
			</p>
		{:else if phase === 'writing'}
			<p class="mt-3 text-sm">The AI is reading the portfolio…</p>
		{/if}
		{#if phase === 'stopped'}<p class="mt-2 text-sm">Stopped.</p>{/if}
		{#if error}<p role="alert" class="mt-2 text-sm text-weak">{error}</p>{/if}
	</div>
	<p class="mt-3 text-xs">
		The AI sees each project's verdict, weakest link and answered count, not the evidence. Verdicts
		come from the rules.
	</p>
</section>

<style>
	.cursor {
		animation: blink 1s steps(2) infinite;
	}
	@keyframes blink {
		to {
			opacity: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.cursor {
			animation: none;
		}
	}
</style>
