/**
 * Makes a <details> element behave like a menu: it closes on a click outside,
 * on Escape (focus goes back to the button) and after a choice inside it.
 */
export function menu(node: HTMLDetailsElement) {
	const close = (refocus: boolean) => {
		if (!node.open) return;
		node.open = false;
		if (refocus) node.querySelector('summary')?.focus();
	};
	const onClick = (e: MouseEvent) => {
		const target = e.target as Element;
		if (!node.contains(target)) close(false);
		else if (target.closest('a, button')) close(false); // a choice was made
	};
	const onKey = (e: KeyboardEvent) => {
		if (e.key === 'Escape') close(true);
	};
	document.addEventListener('click', onClick);
	node.addEventListener('keydown', onKey);
	return {
		destroy() {
			document.removeEventListener('click', onClick);
			node.removeEventListener('keydown', onKey);
		}
	};
}
