import { api, ApiError, type User } from './api';

// The signed-in user, shared by every screen.
export const session = $state<{ user: User | null; loaded: boolean }>({
	user: null,
	loaded: false
});

/** Load the user. Returns false when nobody is signed in. */
export async function loadSession(): Promise<boolean> {
	try {
		session.user = await api<User>('/me');
		return true;
	} catch (e) {
		if (e instanceof ApiError && e.status === 401) {
			session.user = null;
			return false;
		}
		throw e;
	} finally {
		session.loaded = true;
	}
}
