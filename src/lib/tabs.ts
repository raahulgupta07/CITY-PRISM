/**
 * Arrow keys, Home and End move between tabs, as screen-reader users expect.
 * Tab buttons need the id `${idPrefix}${key}`.
 */
export function tabKeys<K extends string | number>(
	e: KeyboardEvent,
	keys: readonly K[],
	current: K,
	select: (key: K) => void,
	idPrefix: string
) {
	const i = keys.indexOf(current);
	const n = keys.length;
	const to: Record<string, number> = {
		ArrowRight: (i + 1) % n,
		ArrowLeft: (i - 1 + n) % n,
		Home: 0,
		End: n - 1
	};
	if (!(e.key in to)) return;
	e.preventDefault();
	const next = keys[to[e.key]];
	select(next);
	document.getElementById(`${idPrefix}${next}`)?.focus();
}
