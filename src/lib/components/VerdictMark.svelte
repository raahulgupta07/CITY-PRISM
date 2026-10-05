<script lang="ts">
	import type { Score } from '$lib/api';
	import { VERDICT_FILL } from '$lib/colours';
	import { VERDICT_LABELS } from '$lib/scoring';

	let {
		score,
		showPartial = true,
		dark = false
	}: { score: Score; showPartial?: boolean; dark?: boolean } = $props();

	const partial = $derived(showPartial && score.partial && score.verdict !== 'not_assessed');
</script>

<span class="inline-flex items-center gap-2 whitespace-nowrap">
	{#if score.verdict === 'not_assessed'}
		<span aria-hidden="true" class="inline-block size-2 border border-hollow"></span>
	{:else}
		<span
			aria-hidden="true"
			class="inline-block size-2"
			style:background={VERDICT_FILL[score.verdict]}
		></span>
	{/if}
	<span
		>{VERDICT_LABELS[score.verdict]}{#if partial}<span
				class="ml-1 {dark ? 'text-band-muted' : 'text-muted'}">(partial)</span
			>{/if}</span
	>
</span>
