import { describe, expect, it } from 'vitest';
import cases from '../../shared/scoring_cases.json';
import { scoreDimension, scoreProject, summarise } from './scoring';

describe('scoreDimension', () => {
	for (const c of cases.dimension_cases) {
		it(c.name, () => {
			const d = scoreDimension(c.answers);
			expect(d.raw).toBe(c.raw);
			expect(d.score).toBe(c.score);
			expect(d.capped).toBe(c.capped);
			expect(d.has_no).toBe(c.has_no);
			expect(d.answered).toBe(c.answered);
		});
	}
});

describe('summarise', () => {
	for (const c of cases.summary_cases) {
		it(c.name, () => {
			const s = summarise(c.dimension_scores as Record<string, number | null>, c.answered);
			expect(s.lowest).toBe(c.lowest);
			expect(s.weakest).toEqual(c.weakest);
			expect(s.verdict).toBe(c.verdict);
			expect(s.partial).toBe(c.partial);
		});
	}
});

describe('scoreProject', () => {
	for (const c of cases.project_cases) {
		it(c.name, () => {
			const r = scoreProject(c.answers as Record<string, string | null>);
			expect(r.dimension_scores).toEqual(
				Object.fromEntries(Object.entries(c.dimension_scores).map(([k, v]) => [Number(k), v]))
			);
			expect(r.lowest).toBe(c.lowest);
			expect(r.weakest).toEqual(c.weakest);
			expect(r.verdict).toBe(c.verdict);
			expect(r.answered).toBe(c.answered);
			expect(r.coverage).toBeCloseTo(c.coverage, 10);
			expect(r.partial).toBe(c.partial);
		});
	}
});
