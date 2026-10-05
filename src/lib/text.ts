// Sentences built from the rules result. No AI here: the same numbers always
// give the same words.

import type { Score } from './api';
import { VERDICT_LABELS } from './scoring';

export const DIM_SHORT: Record<number, string> = {
	1: 'Strategy',
	2: 'Ownership',
	3: 'Data',
	4: 'Technology',
	5: 'Quality',
	6: 'Workflow',
	7: 'People',
	8: 'Value'
};
export const DIM_ABBR: Record<number, string> = {
	1: 'Str',
	2: 'Own',
	3: 'Dat',
	4: 'Tec',
	5: 'Qua',
	6: 'Wfl',
	7: 'Ppl',
	8: 'Val'
};
// What a project "must fix" when this dimension is its weakest.
const DIM_NOUN: Record<number, string> = {
	1: 'strategy',
	2: 'ownership',
	3: 'data',
	4: 'technology',
	5: 'quality checks',
	6: 'workflow',
	7: 'adoption plan',
	8: 'value tracking'
};

const WORDS = [
	'no',
	'one',
	'two',
	'three',
	'four',
	'five',
	'six',
	'seven',
	'eight',
	'nine',
	'ten',
	'eleven',
	'twelve'
];

export function numberWord(n: number): string {
	return n < WORDS.length ? WORDS[n] : String(n);
}

function cap(s: string): string {
	return s.charAt(0).toUpperCase() + s.slice(1);
}

export function joinAnd(items: string[]): string {
	if (items.length <= 1) return items.join('');
	return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

export function formatScore(v: number | null): string {
	return v === null ? '–' : v.toFixed(1);
}

/** Count how often each dimension is a weakest link (ties count for each). */
export function stuckCounts(scores: Score[]): { id: number; n: number }[] {
	const counts = new Map<number, number>();
	for (const s of scores) for (const d of s.weakest) counts.set(d, (counts.get(d) ?? 0) + 1);
	return [...counts.entries()]
		.map(([id, n]) => ({ id, n }))
		.sort((a, b) => b.n - a.n || a.id - b.id);
}

/** The headline and the line below it on the portfolio. */
export function portfolioSentences(scores: Score[]): { headline: string; detail: string } {
	const count = { fix: 0, go: 0, ready: 0, not_assessed: 0 };
	for (const s of scores) count[s.verdict] += 1;
	const detail: string[] = [];
	let headline: string;

	if (scores.length === 0) {
		return { headline: 'No projects yet.', detail: 'Add the first project to start.' };
	}
	if (count.fix > 0) {
		const fixes = scores.filter((s) => s.verdict === 'fix');
		const first = fixes[0].weakest;
		const shared =
			first.length === 1 && fixes.every((s) => s.weakest.length === 1 && s.weakest[0] === first[0])
				? first[0]
				: null;
		const their = count.fix === 1 ? 'its' : 'their';
		const area = shared ? `${their} ${DIM_NOUN[shared]}` : `${their} weakest area`;
		const subject =
			count.fix === 1 ? 'One project must' : `${cap(numberWord(count.fix))} projects must`;
		headline = `${subject} fix ${area} before the next stage.`;
		if (count.go) detail.push(`${cap(numberWord(count.go))} can go ahead with actions.`);
	} else if (count.go > 0) {
		headline = `No project has to stop. ${cap(numberWord(count.go))} can go ahead with actions.`;
	} else if (count.ready > 0) {
		headline =
			count.ready === 1
				? 'One project is ready.'
				: `${cap(numberWord(count.ready))} projects are ready.`;
	} else {
		headline = 'No project has answers yet.';
	}
	if (count.ready && (count.fix || count.go)) {
		detail.push(`${cap(numberWord(count.ready))} ${count.ready === 1 ? 'is' : 'are'} ready.`);
	}
	if (count.not_assessed && count.not_assessed < scores.length) {
		detail.push(
			`${cap(numberWord(count.not_assessed))} ${count.not_assessed === 1 ? 'has' : 'have'} no answers yet.`
		);
	}
	const stuck = stuckCounts(scores);
	if (stuck.length) {
		const top = stuck.filter((s) => s.n === stuck[0].n).map((s) => DIM_SHORT[s.id]);
		detail.push(
			top.length === 1
				? `${top[0]} is the most common weakest link.`
				: `${joinAnd(top)} are the most common weakest links.`
		);
	}
	return { headline, detail: detail.join(' ') };
}

/** The sentence under a project name on the Assess screen. */
export function projectSentence(score: Score, total = 40): string {
	const open = total - score.answered;
	const openText =
		open === 0
			? 'All questions are answered.'
			: open === 1
				? '1 question is still open.'
				: `${open} questions are still open.`;
	if (score.verdict === 'not_assessed') return `Not assessed yet. ${openText}`;
	const names = joinAnd(score.weakest.map((d) => DIM_SHORT[d]));
	const low = formatScore(score.lowest);
	const middle =
		score.verdict === 'ready'
			? `The lowest score is ${low}, in ${names}.`
			: `${names} ${score.weakest.length > 1 ? 'hold' : 'holds'} it back at ${low}.`;
	return `${VERDICT_LABELS[score.verdict]}. ${middle} ${openText}`;
}

/** Whole days from today to the due date (negative when past). */
export function daysLeft(due: string, today: Date = new Date()): number {
	const [y, m, d] = due.split('-').map(Number);
	const end = Date.UTC(y, m - 1, d);
	const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
	return Math.round((end - start) / 86_400_000);
}

export function formatDate(iso: string | null): string {
	if (!iso) return '';
	const d = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
	return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatDateTime(iso: string): string {
	return new Date(iso).toLocaleString('en-GB', {
		day: 'numeric',
		month: 'short',
		hour: '2-digit',
		minute: '2-digit'
	});
}
