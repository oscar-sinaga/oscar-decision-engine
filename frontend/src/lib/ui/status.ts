import {
	AlertCircle,
	Ban,
	Check,
	CircleDashed,
	Clock3,
	FileCheck2,
	Flag,
	Info,
	OctagonAlert,
	Pause,
	ShieldAlert,
	SkipForward,
	Sparkles,
	UserRoundCheck,
	X
} from '@lucide/svelte';
import type { Component } from 'svelte';

export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'special' | 'neutral';
export interface StatusDefinition {
	label: string;
	tone: StatusTone;
	icon: Component;
}

const success = (label: string, icon: Component = Check): StatusDefinition => ({
	label,
	tone: 'success',
	icon
});
const warning = (label: string, icon: Component = Clock3): StatusDefinition => ({
	label,
	tone: 'warning',
	icon
});
const danger = (label: string, icon: Component = X): StatusDefinition => ({
	label,
	tone: 'danger',
	icon
});
const info = (label: string, icon: Component = Info): StatusDefinition => ({
	label,
	tone: 'info',
	icon
});
const special = (label: string, icon: Component = Sparkles): StatusDefinition => ({
	label,
	tone: 'special',
	icon
});
const neutral = (label: string, icon: Component = CircleDashed): StatusDefinition => ({
	label,
	tone: 'neutral',
	icon
});

export const STATUS_MAP: Record<string, StatusDefinition> = {
	ACTIVE: success('Active'),
	APPROVE: success('Approve'),
	APPROVED: success('Approved'),
	RECEIVED: success('Received', FileCheck2),
	RESOLVED: success('Resolved'),
	COMPLETED: success('Completed'),
	PASS: success('Pass'),
	PASSED: success('Passed'),
	PENDING_APPROVAL: warning('Pending approval'),
	MANUAL_REVIEW: warning('Manual review'),
	IN_REVIEW: warning('In review'),
	PENDING_DOCUMENTS: warning('Pending documents'),
	APPROVE_WITH_CONDITION: warning('Approve with condition'),
	PENDING: warning('Pending'),
	HIGH: warning('High', Flag),
	REJECT: danger('Reject'),
	REJECTED: danger('Rejected'),
	BREACHED: danger('Breached', OctagonAlert),
	FAIL: danger('Fail', AlertCircle),
	FAILED: danger('Failed', AlertCircle),
	ERROR: danger('Error', AlertCircle),
	CRITICAL: danger('Critical', OctagonAlert),
	DRAFT: info('Draft'),
	NEW: info('New'),
	ASSIGNED: info('Assigned', UserRoundCheck),
	SIMULATION: info('Simulation'),
	OPEN: info('Open'),
	FRAUD_INVESTIGATION: special('Fraud investigation', ShieldAlert),
	ESCALATED: special('Escalated', ShieldAlert),
	OVERRIDE: special('Override', ShieldAlert),
	RETIRED: neutral('Retired', Pause),
	SKIP: neutral('Skip', SkipForward),
	SKIPPED: neutral('Skipped', SkipForward),
	CLOSED: neutral('Closed'),
	WAIVED: neutral('Waived'),
	LOW: neutral('Low'),
	MEDIUM: info('Medium'),
	TRUE: success('True'),
	FALSE: danger('False', Ban)
};

export function resolveStatus(value: string): StatusDefinition {
	const normalized = value.trim().toUpperCase();
	return STATUS_MAP[normalized] ?? neutral(value.replaceAll('_', ' '));
}
