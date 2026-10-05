import type { AnswerRow, Dimension, Question } from './api';

/**
 * The next question for the interview: unanswered questions in the current
 * dimension first, then the rest in order (SPEC 6.2). Skipped ones are left out.
 */
export function nextQuestion(
	dims: Dimension[],
	answers: Record<string, AnswerRow | undefined>,
	current: number,
	skipped: Set<string>
): Question | null {
	const open = (q: Question) => q.active && !answers[q.id]?.answer && !skipped.has(q.id);
	const here = dims.find((d) => d.id === current)?.questions.find(open);
	if (here) return here;
	for (const d of dims) {
		const q = d.questions.find(open);
		if (q) return q;
	}
	return null;
}
