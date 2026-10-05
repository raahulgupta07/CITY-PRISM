import { describe, expect, it } from 'vitest';
import type { AnswerRow, Dimension } from './api';
import { nextQuestion } from './interview';

const dims: Dimension[] = [1, 2].map((d) => ({
	id: d,
	title: `D${d}`,
	group_name: '',
	lead_question: '',
	sort_order: d,
	questions: [1, 2].map((n) => ({
		id: `${d}.${n}`,
		dimension_id: d,
		number: n,
		text: '',
		is_draft: false,
		active: true,
		version: 1
	}))
}));
const answered = (answer: AnswerRow['answer']) => ({ answer }) as AnswerRow;

describe('nextQuestion', () => {
	it('starts in the current dimension', () => {
		expect(nextQuestion(dims, {}, 2, new Set())?.id).toBe('2.1');
	});
	it('moves on to other dimensions in order', () => {
		const a = { '2.1': answered('Yes'), '2.2': answered('No') };
		expect(nextQuestion(dims, a, 2, new Set())?.id).toBe('1.1');
	});
	it('treats a cleared answer as open and leaves out skipped ones', () => {
		const a = { '1.1': answered(null) };
		expect(nextQuestion(dims, a, 1, new Set())?.id).toBe('1.1');
		expect(nextQuestion(dims, a, 1, new Set(['1.1']))?.id).toBe('1.2');
	});
	it('returns null when everything is answered or skipped', () => {
		expect(nextQuestion(dims, {}, 1, new Set(['1.1', '1.2', '2.1', '2.2']))).toBeNull();
	});
});
