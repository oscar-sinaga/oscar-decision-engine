// Display formatting helpers for the workbench.

const idr = new Intl.NumberFormat('id-ID', {
	style: 'currency',
	currency: 'IDR',
	maximumFractionDigits: 0
});

export function formatCurrency(value: number | null | undefined): string {
	if (value === null || value === undefined) return '—';
	return idr.format(value);
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
	if (value === null || value === undefined) return '—';
	return `${(value * 100).toFixed(digits)}%`;
}

export function formatDateTime(value: string | null | undefined): string {
	if (!value) return '—';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return date.toLocaleString('en-GB', {
		day: '2-digit',
		month: 'short',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

export function decisionBadgeClass(decision: string): string {
	switch (decision) {
		case 'APPROVE':
			return 'bg-emerald-100 text-emerald-800';
		case 'APPROVE_WITH_CONDITION':
			return 'bg-lime-100 text-lime-800';
		case 'REJECT':
			return 'bg-red-100 text-red-800';
		case 'MANUAL_REVIEW':
			return 'bg-amber-100 text-amber-800';
		case 'FRAUD_INVESTIGATION':
			return 'bg-purple-100 text-purple-800';
		case 'ERROR':
			return 'bg-gray-200 text-gray-800';
		default:
			return 'bg-slate-100 text-slate-700';
	}
}

export function statusBadgeClass(status: string): string {
	switch (status) {
		case 'ACTIVE':
		case 'COMPLETED':
		case 'APPROVED':
		case 'APPROVED_BY_ANALYST':
			return 'bg-emerald-100 text-emerald-800';
		case 'DRAFT':
		case 'NEW':
			return 'bg-sky-100 text-sky-800';
		case 'PENDING_APPROVAL':
		case 'PENDING':
		case 'PENDING_DOCUMENTS':
		case 'ASSIGNED':
		case 'IN_REVIEW':
			return 'bg-amber-100 text-amber-800';
		case 'RETIRED':
		case 'CLOSED':
			return 'bg-slate-200 text-slate-600';
		case 'REJECTED':
		case 'REJECTED_BY_ANALYST':
		case 'FAILED':
			return 'bg-red-100 text-red-800';
		case 'ESCALATED':
			return 'bg-purple-100 text-purple-800';
		default:
			return 'bg-slate-100 text-slate-700';
	}
}
