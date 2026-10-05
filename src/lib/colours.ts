import type { Verdict } from './scoring';

/** Colours used from scripts. They point at the tokens in app.css, so dark mode follows. */
const v = (name: string) => `var(--color-${name})`;

export const VERDICT_FILL: Record<Verdict, string> = {
	fix: v('weak'),
	go: v('go'),
	ready: v('strong'),
	not_assessed: 'transparent'
};

/** Verdict colours for text and marks on the dark band. */
export const VERDICT_ON_DARK: Record<Verdict, string> = {
	fix: v('weak-on-dark'),
	go: v('partial-on-dark'),
	ready: v('strong-on-dark'),
	not_assessed: '#ffffff'
};

/** Dimension band colours on the dark band. */
export const BAND_ON_DARK = {
	weak: v('weak-on-dark'),
	partial: v('partial-on-dark'),
	strong: v('strong-on-dark'),
	none: v('band-line')
};

/** Half-strength version of a colour, for bars that are not the weakest link. */
export const faded = (colour: string) => `color-mix(in srgb, ${colour} 50%, transparent)`;
