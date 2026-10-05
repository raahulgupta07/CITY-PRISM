<script lang="ts">
	import { ANSWER_LABELS, ANSWER_VALUES, type AnswerValue } from '$lib/api';

	let {
		value,
		label,
		disabled = false,
		aiUnconfirmed = false,
		onpick
	}: {
		value: AnswerValue | null;
		label: string;
		disabled?: boolean;
		aiUnconfirmed?: boolean;
		onpick: (v: AnswerValue | null) => void;
	} = $props();

	const ON: Record<AnswerValue, string> = {
		Yes: 'bg-[#1F7A4C] text-white',
		Partly: 'bg-partial text-[#2B1C00]',
		No: 'bg-weak text-white',
		Dont_know: 'bg-[#4A5465] text-white'
	};
</script>

<!-- Click the selected answer again to clear it. -->
<div role="group" aria-label={label} class="inline-flex border border-line bg-white">
	{#each ANSWER_VALUES as v, i (v)}
		{@const on = value === v}
		<button
			type="button"
			aria-pressed={on}
			{disabled}
			title={on && !disabled ? 'Click again to clear' : undefined}
			class="min-h-11 px-3 text-[13px] whitespace-nowrap sm:px-3.5 {i
				? 'border-l border-line'
				: ''} {on
				? `${ON[v]} font-semibold`
				: 'text-muted hover:bg-canvas'} disabled:cursor-default"
			class:ai={on && aiUnconfirmed}
			onclick={() => onpick(on ? null : v)}>{ANSWER_LABELS[v]}</button
		>
	{/each}
</div>

<style>
	.ai {
		outline: 2px dashed var(--color-ai-ink);
		outline-offset: -4px;
	}
</style>
