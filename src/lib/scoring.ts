// Mirror of backend/app/scoring.py so the screen can update at once.
// The server stays the source of truth. Both run shared/scoring_cases.json.

export type Answer = 'Yes' | 'Partly' | 'No' | 'Dont_know';
export type Verdict = 'fix' | 'go' | 'ready' | 'not_assessed';
export type Band = 'weak' | 'partial' | 'strong' | 'none';

export const POINTS: Record<Answer, number> = { Yes: 5, Partly: 3, No: 1, Dont_know: 1 };
export const DIMENSION_IDS = [1, 2, 3, 4, 5, 6, 7, 8] as const;
export const TOTAL_QUESTIONS = 40;
const NO_CAP = 3.0;
const FIX_MAX = 2.4;
const GO_MAX = 3.4;

export const VERDICT_LABELS: Record<Verdict, string> = {
	fix: 'Fix before next stage',
	go: 'Go with actions',
	ready: 'Ready',
	not_assessed: 'Not assessed'
};
export const VERDICT_ORDER: Record<Verdict, number> = { fix: 0, go: 1, ready: 2, not_assessed: 3 };

export interface DimensionScore {
	id: number;
	score: number | null;
	raw: number | null;
	capped: boolean;
	has_no: boolean;
	answered: number;
	band: Band;
}

export interface Summary {
	lowest: number | null;
	weakest: number[];
	verdict: Verdict;
	partial: boolean;
}

export interface ScoreResult extends Summary {
	dimensions: DimensionScore[];
	answered: number;
	coverage: number;
	dimension_scores: Record<number, number | null>;
}

function isAnswer(a: unknown): a is Answer {
	return typeof a === 'string' && a in POINTS;
}

/** Round to 1 decimal, halves away from zero (same as the server). */
export function round1(value: number): number {
	return Math.round((value + Number.EPSILON) * 10) / 10;
}

export function band(score: number | null): Band {
	if (score === null) return 'none';
	if (score <= FIX_MAX) return 'weak';
	if (score <= GO_MAX) return 'partial';
	return 'strong';
}

/** Average the answered questions; any No caps the score at 3.0. */
export function scoreDimension(answers: (string | null)[], id = 0): DimensionScore {
	const given = answers.filter(isAnswer);
	if (given.length === 0) {
		return { id, score: null, raw: null, capped: false, has_no: false, answered: 0, band: 'none' };
	}
	const raw = round1(given.reduce((sum, a) => sum + POINTS[a], 0) / given.length);
	const has_no = given.includes('No');
	const capped = has_no && raw > NO_CAP;
	const score = capped ? NO_CAP : raw;
	return { id, score, raw, capped, has_no, answered: given.length, band: band(score) };
}

/** Lowest, weakest link and verdict from the dimension scores. */
export function summarise(
	dimensionScores: Record<number | string, number | null>,
	answered: number
): Summary {
	const partial = answered < TOTAL_QUESTIONS;
	const scored = Object.entries(dimensionScores)
		.filter((e): e is [string, number] => e[1] !== null)
		.map(([k, v]) => [Number(k), v] as const);
	if (scored.length === 0) return { lowest: null, weakest: [], verdict: 'not_assessed', partial };
	const lowest = Math.min(...scored.map(([, v]) => v));
	const weakest = scored
		.filter(([, v]) => v === lowest)
		.map(([k]) => k)
		.sort((a, b) => a - b);
	const verdict: Verdict = lowest <= FIX_MAX ? 'fix' : lowest <= GO_MAX ? 'go' : 'ready';
	return { lowest, weakest, verdict, partial };
}

/** '5.1' -> 5. Anything that is not a known dimension returns null. */
export function dimensionOf(questionId: string): number | null {
	const m = /^(\d+)\.(\d+)$/.exec(questionId);
	if (!m) return null;
	const dim = Number(m[1]);
	return (DIMENSION_IDS as readonly number[]).includes(dim) ? dim : null;
}

/** answers maps question ID ('5.1') to an answer or null (blank). */
export function scoreProject(answers: Record<string, string | null>): ScoreResult {
	const byDim = new Map<number, (string | null)[]>(DIMENSION_IDS.map((d) => [d, []]));
	for (const [qid, answer] of Object.entries(answers)) {
		const dim = dimensionOf(qid);
		if (dim !== null) byDim.get(dim)!.push(answer);
	}
	const dimensions = DIMENSION_IDS.map((d) => scoreDimension(byDim.get(d)!, d));
	const answered = dimensions.reduce((n, d) => n + d.answered, 0);
	const dimension_scores = Object.fromEntries(dimensions.map((d) => [d.id, d.score]));
	return {
		dimensions,
		...summarise(dimension_scores, answered),
		answered,
		coverage: answered / TOTAL_QUESTIONS,
		dimension_scores
	};
}
