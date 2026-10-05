// Thin wrapper over fetch for /api. The browser only ever talks to our server.

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
	const res = await fetch(`/api${path}`, {
		credentials: 'same-origin',
		...init,
		// Let the browser set the multipart boundary for file uploads.
		headers:
			init.body instanceof FormData
				? (init.headers ?? {})
				: { 'Content-Type': 'application/json', ...(init.headers ?? {}) }
	});
	if (!res.ok) {
		let message = 'Something went wrong. Please try again.';
		try {
			const body = await res.json();
			if (typeof body?.detail === 'string') message = body.detail;
		} catch {
			// keep the default message
		}
		throw new ApiError(res.status, message);
	}
	return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export type Role = 'owner' | 'reviewer' | 'approver' | 'admin';

export interface User {
	id: string;
	name: string;
	email: string;
	role: Role;
}

export interface AuthOptions {
	provider: 'dev' | 'none';
	users: { name: string; email: string; role: Role }[];
}

export const ROLE_LABELS: Record<Role, string> = {
	owner: 'Project owner',
	reviewer: 'Reviewer',
	approver: 'Approver',
	admin: 'Admin'
};

// ---- Framework, projects, answers ----

export type Stage = 'Idea' | 'Feasibility' | 'Build' | 'Pilot / UAT' | 'Production' | 'On hold';
export type Mode = 'plan' | 'assess';
export type AnswerValue = 'Yes' | 'Partly' | 'No' | 'Dont_know';

export const STAGES: Stage[] = [
	'Idea',
	'Feasibility',
	'Build',
	'Pilot / UAT',
	'Production',
	'On hold'
];
export const MODE_LABELS: Record<Mode, string> = {
	plan: 'Planning a new project',
	assess: 'Assessing an existing project'
};
export const ANSWER_LABELS: Record<AnswerValue, string> = {
	Yes: 'Yes',
	Partly: 'Partly',
	No: 'No',
	Dont_know: "Don't know"
};
export const ANSWER_VALUES: AnswerValue[] = ['Yes', 'Partly', 'No', 'Dont_know'];
export const EVIDENCE_MAX = 600;
export const DUE_DATE = '2026-10-30';

export interface Question {
	id: string;
	dimension_id: number;
	number: number;
	text: string;
	is_draft: boolean;
	active: boolean;
	version: number;
}

export interface Dimension {
	id: number;
	title: string;
	group_name: string;
	lead_question: string;
	sort_order: number;
	questions: Question[];
}

export interface UserRef {
	id: string;
	name: string;
}

export interface DimensionScore {
	id: number;
	score: number | null;
	raw: number | null;
	capped: boolean;
	has_no: boolean;
	answered: number;
	band: 'weak' | 'partial' | 'strong' | 'none';
}

export interface Score {
	dimensions: DimensionScore[];
	lowest: number | null;
	weakest: number[];
	verdict: 'fix' | 'go' | 'ready' | 'not_assessed';
	answered: number;
	coverage: number;
	partial: boolean;
}

export interface Project {
	id: string;
	name: string;
	business_unit: string;
	sponsor: string;
	owner: UserRef | null;
	stage: Stage;
	mode: Mode;
	due_date: string | null;
	archived: boolean;
	created_at: string;
	updated_at: string;
	can_edit: boolean;
	score: Score;
}

export interface AnswerRow {
	question_id: string;
	answer: AnswerValue | null;
	evidence: string;
	source: 'person' | 'ai_interview' | 'ai_evidence';
	confirmed: boolean;
	updated_by: UserRef | null;
	updated_at: string;
}

export interface ProjectDetail extends Project {
	answers: AnswerRow[];
}

export interface AnswerSaved {
	answer: AnswerRow;
	score: Score;
	changed: boolean;
}

export interface HistoryRow {
	id: number;
	question_id: string;
	old_answer: AnswerValue | null;
	new_answer: AnswerValue | null;
	old_evidence: string;
	new_evidence: string;
	source: 'person' | 'ai_interview' | 'ai_evidence' | 'confirm' | 'undo';
	changed_by: UserRef | null;
	changed_at: string;
}

// ---- Agent ----

export interface InterviewOut {
	answer: 'Yes' | 'Partly' | 'No' | "Don't know" | '';
	evidence: string;
	followUp: string;
	saved: AnswerSaved | null;
}

export interface Suggestion {
	id: string;
	question_id: string;
	answer: 'Yes' | 'Partly' | 'No';
	evidence: string;
	source_excerpt: string;
	status: 'pending' | 'accepted' | 'dismissed';
	created_at: string;
}

export interface EvidenceOut {
	file_id: string;
	filename: string;
	chars_read: number;
	truncated: boolean;
	suggestions: Suggestion[];
}

export interface SuggestionDone {
	suggestion: Suggestion;
	saved: AnswerSaved | null;
}

export interface AcceptAllOut {
	accepted: number;
	answers: AnswerRow[];
	score: Score;
}

// ---- Decision brief ----

export interface BriefAction {
	question_id: string;
	action: string;
	owner: string;
}

export interface Brief {
	id: string;
	project_id: string;
	created_at: string;
	created_by: UserRef | null;
	// Snapshot of the rules result when the brief was written. Never from AI.
	verdict: Score['verdict'];
	lowest: number | null;
	weakest: number[];
	dimensions: DimensionScore[];
	answered: number;
	// Written by AI.
	headline: string;
	summary: string;
	actions: BriefAction[];
	risks: string[];
	approved: boolean;
	approved_by: UserRef | null;
	approved_at: string | null;
	changed_since: boolean;
}
