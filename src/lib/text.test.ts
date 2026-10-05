import { describe, expect, it } from 'vitest';
import type { Score } from './api';
import { daysLeft, joinAnd, portfolioSentences, projectSentence, stuckCounts } from './text';

function s(
	verdict: Score['verdict'],
	weakest: number[],
	lowest: number | null,
	answered = 2
): Score {
	return {
		dimensions: [],
		verdict,
		weakest,
		lowest,
		answered,
		coverage: answered / 40,
		partial: true
	};
}

// The 12 seed projects (SPEC section 9).
const SEED: Score[] = [
	s('fix', [3], 1.0),
	s('fix', [3], 1.0),
	s('go', [2, 5], 3.0, 8),
	s('go', [7], 3.0, 3),
	s('go', [3, 5], 3.0),
	s('go', [5, 7], 3.0),
	s('go', [4, 7], 3.0),
	s('go', [7], 3.0, 1),
	s('ready', [5, 7], 5.0),
	s('not_assessed', [], null, 0),
	s('not_assessed', [], null, 0),
	s('not_assessed', [], null, 0)
];

describe('portfolioSentences', () => {
	it('matches the mockup for the seed data', () => {
		expect(portfolioSentences(SEED)).toEqual({
			headline: 'Two projects must fix their data before the next stage.',
			detail:
				'Six can go ahead with actions. One is ready. Three have no answers yet. People is the most common weakest link.'
		});
	});
	it('says weakest area when fix projects differ', () => {
		const r = portfolioSentences([s('fix', [3], 1), s('fix', [5], 2)]);
		expect(r.headline).toBe('Two projects must fix their weakest area before the next stage.');
		expect(r.detail).toBe('Data and Quality are the most common weakest links.');
	});
	it('handles one fix', () => {
		expect(portfolioSentences([s('fix', [2], 1)]).headline).toBe(
			'One project must fix its ownership before the next stage.'
		);
	});
	it('handles no fix', () => {
		expect(portfolioSentences([s('go', [1], 3), s('ready', [1], 4)]).headline).toBe(
			'No project has to stop. One can go ahead with actions.'
		);
		expect(portfolioSentences([s('ready', [1], 4)]).headline).toBe('One project is ready.');
	});
	it('handles nothing assessed and no projects', () => {
		expect(portfolioSentences([s('not_assessed', [], null, 0)])).toEqual({
			headline: 'No project has answers yet.',
			detail: ''
		});
		expect(portfolioSentences([]).headline).toBe('No projects yet.');
	});
});

describe('projectSentence', () => {
	it('go with two weakest', () => {
		expect(projectSentence(s('go', [2, 5], 3.0, 8))).toBe(
			'Go with actions. Ownership and Quality hold it back at 3.0. 32 questions are still open.'
		);
	});
	it('fix with one weakest', () => {
		expect(projectSentence(s('fix', [3], 1.0, 39))).toBe(
			'Fix before next stage. Data holds it back at 1.0. 1 question is still open.'
		);
	});
	it('ready and complete', () => {
		expect(projectSentence(s('ready', [8], 4.6, 40))).toBe(
			'Ready. The lowest score is 4.6, in Value. All questions are answered.'
		);
	});
	it('not assessed', () => {
		expect(projectSentence(s('not_assessed', [], null, 0))).toBe(
			'Not assessed yet. 40 questions are still open.'
		);
	});
});

describe('helpers', () => {
	it('stuckCounts', () => {
		expect(stuckCounts(SEED).slice(0, 2)).toEqual([
			{ id: 7, n: 5 },
			{ id: 5, n: 4 }
		]);
	});
	it('joinAnd', () => {
		expect(joinAnd(['A', 'B', 'C'])).toBe('A, B and C');
	});
	it('daysLeft', () => {
		expect(daysLeft('2026-10-30', new Date(2026, 9, 5))).toBe(25);
		expect(daysLeft('2026-10-30', new Date(2026, 10, 1))).toBe(-2);
	});
});
