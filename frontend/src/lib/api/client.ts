// Thin typed API client. Every call carries the bearer token; errors are
// normalized to ApiError carrying the backend's safe error envelope.

import type { ApiErrorBody } from './types';

export const API_BASE =
	(import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

export class ApiError extends Error {
	readonly code: string;
	readonly status: number;
	readonly details: { field?: string; issue?: string }[];
	readonly correlationId: string | null;

	constructor(status: number, body: ApiErrorBody | null, fallback: string) {
		super(body?.error?.message ?? fallback);
		this.status = status;
		this.code = body?.error?.code ?? 'UNKNOWN_ERROR';
		this.details = body?.error?.details ?? [];
		this.correlationId = body?.correlation_id ?? null;
	}

	get detailText(): string {
		return this.details
			.map((d) => (d.field ? `${d.field}: ${d.issue ?? ''}` : (d.issue ?? '')))
			.join('; ');
	}
}

let tokenProvider: () => string | null = () => null;
let onUnauthorized: () => void = () => {};

export function configureClient(options: {
	getToken: () => string | null;
	handleUnauthorized: () => void;
}): void {
	tokenProvider = options.getToken;
	onUnauthorized = options.handleUnauthorized;
}

export interface RequestOptions {
	method?: string;
	body?: unknown;
	query?: Record<string, string | number | boolean | undefined | null>;
	headers?: Record<string, string>;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
	const url = new URL(
		`${API_BASE}${path}`,
		typeof window === 'undefined' ? 'http://localhost' : window.location.origin
	);
	for (const [key, value] of Object.entries(options.query ?? {})) {
		if (value !== undefined && value !== null && value !== '') {
			url.searchParams.set(key, String(value));
		}
	}
	const headers: Record<string, string> = { ...options.headers };
	const token = tokenProvider();
	if (token) headers['Authorization'] = `Bearer ${token}`;
	if (options.body !== undefined) headers['Content-Type'] = 'application/json';

	const response = await fetch(url, {
		method: options.method ?? (options.body !== undefined ? 'POST' : 'GET'),
		headers,
		body: options.body !== undefined ? JSON.stringify(options.body) : undefined
	});

	if (!response.ok) {
		let body: ApiErrorBody | null = null;
		try {
			body = (await response.json()) as ApiErrorBody;
		} catch {
			// non-JSON error body: keep the fallback message
		}
		if (response.status === 401) onUnauthorized();
		throw new ApiError(response.status, body, `Request failed (${response.status})`);
	}
	return (await response.json()) as T;
}
