import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, configureClient } from './client';

function mockFetch(status: number, body: unknown) {
	const fetchMock = vi.fn().mockResolvedValue({
		ok: status >= 200 && status < 300,
		status,
		json: () => Promise.resolve(body)
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

afterEach(() => {
	vi.unstubAllGlobals();
	configureClient({ getToken: () => null, handleUnauthorized: () => {} });
});

describe('api client', () => {
	it('sends bearer token and JSON body', async () => {
		configureClient({ getToken: () => 'token-123', handleUnauthorized: () => {} });
		const fetchMock = mockFetch(200, { ok: true });

		await api('/v1/decisions', { body: { application_id: 'APP-1' } });

		const [url, init] = fetchMock.mock.calls[0] as [URL, RequestInit];
		expect(url.toString()).toContain('/v1/decisions');
		expect(init.method).toBe('POST');
		expect((init.headers as Record<string, string>)['Authorization']).toBe('Bearer token-123');
		expect(init.body).toBe(JSON.stringify({ application_id: 'APP-1' }));
	});

	it('serializes query params and skips empty values', async () => {
		const fetchMock = mockFetch(200, {});
		await api('/v1/decisions', { query: { decision: 'REJECT', channel: '', page: 2 } });
		const [url] = fetchMock.mock.calls[0] as [URL];
		expect(url.searchParams.get('decision')).toBe('REJECT');
		expect(url.searchParams.get('page')).toBe('2');
		expect(url.searchParams.has('channel')).toBe(false);
	});

	it('normalizes the backend error envelope', async () => {
		mockFetch(422, {
			error: {
				code: 'VALIDATION_ERROR',
				message: 'Request validation failed',
				details: [{ field: 'vehicle.appraisal_value', issue: 'required' }]
			},
			correlation_id: 'corr-1'
		});

		const failure: unknown = await api('/v1/decisions', { body: {} }).catch((err) => err);
		expect(failure).toBeInstanceOf(ApiError);
		const apiError = failure as ApiError;
		expect(apiError.code).toBe('VALIDATION_ERROR');
		expect(apiError.status).toBe(422);
		expect(apiError.correlationId).toBe('corr-1');
		expect(apiError.detailText).toContain('vehicle.appraisal_value');
	});

	it('invokes the unauthorized handler on 401', async () => {
		const handler = vi.fn();
		configureClient({ getToken: () => 'expired', handleUnauthorized: handler });
		mockFetch(401, {
			error: { code: 'AUTHENTICATION_REQUIRED', message: 'expired', details: [] },
			correlation_id: null
		});

		await expect(api('/v1/auth/me')).rejects.toBeInstanceOf(ApiError);
		expect(handler).toHaveBeenCalledOnce();
	});
});
