export interface ConfirmOptions {
	title: string;
	body?: string;
	confirmLabel: string;
	tone?: 'danger' | 'default';
	requireReason?: boolean;
}
export interface ConfirmResult {
	ok: boolean;
	reason?: string;
}
export function confirmAction(options: ConfirmOptions): Promise<ConfirmResult> {
	if (typeof window === 'undefined') return Promise.resolve({ ok: false });
	return new Promise((resolve) =>
		window.dispatchEvent(new CustomEvent('oscar-confirm', { detail: { options, resolve } }))
	);
}
