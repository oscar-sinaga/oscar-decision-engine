// Auth session state (Svelte 5 runes). Token lives in localStorage; the
// backend enforces authorization — frontend visibility is UX only.

import { api, configureClient } from './api/client';
import type { LoginResponse, MeResponse } from './api/types';

const TOKEN_KEY = 'oscar.token';

class AuthState {
	token = $state<string | null>(null);
	user = $state<MeResponse | null>(null);
	loading = $state(false);

	get isAuthenticated(): boolean {
		return this.token !== null;
	}

	hasPermission(code: string): boolean {
		return this.user?.permissions.includes(code) ?? false;
	}

	initialize(): void {
		if (typeof localStorage === 'undefined') return;
		this.token = localStorage.getItem(TOKEN_KEY);
	}

	async login(username: string, password: string): Promise<void> {
		const response = await api<LoginResponse>('/v1/auth/login', {
			body: { username, password }
		});
		this.token = response.access_token;
		localStorage.setItem(TOKEN_KEY, response.access_token);
		await this.loadProfile();
	}

	async loadProfile(): Promise<void> {
		if (!this.token) return;
		this.loading = true;
		try {
			this.user = await api<MeResponse>('/v1/auth/me');
		} finally {
			this.loading = false;
		}
	}

	logout(): void {
		this.token = null;
		this.user = null;
		if (typeof localStorage !== 'undefined') localStorage.removeItem(TOKEN_KEY);
	}
}

export const auth = new AuthState();

configureClient({
	getToken: () => auth.token,
	handleUnauthorized: () => auth.logout()
});
