/** Light, dark or follow the system. The choice is kept in this browser only. */
export type ThemeChoice = 'system' | 'light' | 'dark';

export const THEME_LABELS: Record<ThemeChoice, string> = {
	system: 'Follow the system',
	light: 'Light',
	dark: 'Dark'
};

// Same key as the script in app.html, which applies the theme before the page draws.
const KEY = 'prism-theme';

function read(): ThemeChoice {
	try {
		const v = localStorage.getItem(KEY);
		return v === 'light' || v === 'dark' ? v : 'system';
	} catch {
		return 'system';
	}
}

export const theme = $state({ choice: read() });

export function setTheme(choice: ThemeChoice) {
	theme.choice = choice;
	try {
		if (choice === 'system') localStorage.removeItem(KEY);
		else localStorage.setItem(KEY, choice);
	} catch {
		// Storage can be blocked. The theme still changes for this visit.
	}
	const dark =
		choice === 'dark' ||
		(choice === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
	document.documentElement.dataset.theme = dark ? 'dark' : 'light';
}
