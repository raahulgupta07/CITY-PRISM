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
		headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) }
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
