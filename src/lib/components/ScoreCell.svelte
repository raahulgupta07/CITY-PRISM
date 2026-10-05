<script lang="ts">
	import type { DimensionScore } from '$lib/api';
	import { DIM_SHORT, formatScore } from '$lib/text';

	let { dim, weakest = false }: { dim: DimensionScore; weakest?: boolean } = $props();

	const STYLE = {
		weak: 'bg-weak text-white',
		partial: 'bg-partial text-[#2B1C00]',
		strong: 'bg-strong text-white',
		none: 'bg-[#F4F5F7] text-[#6B7482]'
	};
	const label = $derived(
		`${DIM_SHORT[dim.id]}: ${dim.score === null ? 'not answered' : formatScore(dim.score)}` +
			` · ${dim.answered} of 5 answered${weakest ? ' · weakest link' : ''}`
	);
</script>

<span
	class="flex h-8 items-center justify-center font-mono text-xs font-medium {STYLE[dim.band]}"
	class:weakest
	title={label}
	aria-label={label}
	role="img">{dim.score === null ? '' : formatScore(dim.score)}</span
>

<style>
	.weakest {
		outline: 2px solid var(--color-ink);
		outline-offset: -2px;
	}
</style>
