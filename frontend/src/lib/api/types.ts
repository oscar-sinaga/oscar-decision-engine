// API DTOs mirroring the FastAPI schemas (docs/07).

export interface ApiErrorBody {
	error: { code: string; message: string; details: { field?: string; issue?: string }[] };
	correlation_id: string | null;
}

export interface LoginResponse {
	access_token: string;
	token_type: string;
}

export interface MeResponse {
	username: string;
	full_name: string;
	roles: string[];
	permissions: string[];
}

export interface ReasonCodeItem {
	code: string;
	message: string;
}

export interface DecisionResponse {
	decision_id: string;
	application_id: string;
	decision: string;
	risk_grade: string | null;
	score: number | null;
	approved_limit: number | null;
	approved_tenor_months: number | null;
	pricing_rate: number | null;
	reason_codes: ReasonCodeItem[];
	strategy_version: string;
	trace_id: string;
	manual_review_case_id: string | null;
	execution_mode: string;
	execution_time_ms: number;
	correlation_id: string | null;
	created_at: string | null;
}

export interface DecisionHistoryItem {
	decision_id: string;
	application_id: string;
	product_type: string;
	channel: string;
	decision: string;
	risk_grade: string | null;
	score: number | null;
	approved_limit: number | null;
	strategy_version_id: string;
	reason_codes: string[];
	created_at: string;
}

export interface Page<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
}

export interface TraceResponse {
	trace_id: string;
	decision_id: string;
	application_id: string;
	execution_mode: string;
	strategy: { strategy_code: string; version: number };
	input_snapshot: Record<string, unknown>;
	feature_values: Record<string, unknown>;
	steps: TraceStep[];
	score_result: Record<string, unknown> | null;
	final_decision: Record<string, unknown>;
	errors: Record<string, unknown>[];
	metadata: { latency_ms: number; request_id: string | null; correlation_id: string | null };
	created_at: string;
}

export interface TraceStep {
	order: number;
	type: string;
	name: string;
	reference_code: string | null;
	reference_version: number | null;
	status: string;
	duration_ms: number;
	rule_results?: RuleResult[];
	[key: string]: unknown;
}

export interface RuleResult {
	rule_code: string;
	version: number;
	matched: boolean;
	status: string;
	evaluated_conditions: EvaluatedCondition[];
	action_applied?: Record<string, unknown>;
}

export interface EvaluatedCondition {
	field: string;
	operator: string;
	expected: unknown;
	actual: unknown;
	field_present: boolean;
	result: boolean;
}

export interface RuleVersion {
	id: string;
	version: number;
	status: string;
	condition: Record<string, unknown>;
	action: Record<string, unknown>;
	version_note: string;
	created_at: string | null;
	effective_from: string | null;
	effective_to: string | null;
}

export interface Rule {
	id: string;
	rule_code: string;
	name: string;
	description: string;
	category: string;
	owner_team: string;
	active_version: number | null;
	latest_version: number;
	latest_status: string;
	created_at: string | null;
	versions?: RuleVersion[];
}

export interface RuleSet {
	id: string;
	code: string;
	name: string;
	description: string;
	rule_codes: string[];
}

export interface ConfigVersion {
	id: string;
	version: number;
	status: string;
	config: Record<string, unknown>;
	version_note: string;
	created_at: string | null;
	warnings: Record<string, unknown>[];
}

export interface ConfigEntity {
	id: string;
	code: string;
	name: string;
	description: string;
	active_version: number | null;
	latest_version: number;
	latest_status: string;
	versions: ConfigVersion[];
}

export interface StrategyStep {
	order: number;
	type: string;
	name: string;
	reference_code: string | null;
	on_error: string;
	config: Record<string, unknown>;
}

export interface StrategyVersion {
	id: string;
	version: number;
	status: string;
	version_note: string;
	steps: StrategyStep[];
	created_at: string | null;
	activated_at: string | null;
	effective_from: string | null;
	effective_to: string | null;
}

export interface Strategy {
	id: string;
	strategy_code: string;
	name: string;
	product_type: string;
	segment: string;
	owner_team: string;
	active_version: number | null;
	latest_version: number | null;
	latest_status: string | null;
	versions?: StrategyVersion[];
}

export interface ReasonCode {
	id: string;
	code: string;
	category: string;
	severity: string;
	internal_message: string;
	customer_message: string | null;
	active: boolean;
}

export interface SimulationOutcome {
	strategy_version: string;
	decision: string;
	risk_grade: string | null;
	score: number | null;
	approved_limit: number | null;
	approved_tenor_months: number | null;
	pricing_rate: number | null;
	reason_codes: string[];
	validation_failures: { field: string; issue: string }[];
}

export interface SimulationResponse {
	simulation_id: string;
	mode: string;
	draft_result: SimulationOutcome;
	active_result: SimulationOutcome | null;
	differences: { field: string; active: unknown; draft: unknown }[];
}

export interface StrategyAggregate {
	strategy_version: string;
	decision_counts: Record<string, number>;
	approval_rate: number;
	reject_rate: number;
	manual_review_rate: number;
	error_rate: number;
	reason_code_distribution: Record<string, number>;
	risk_grade_distribution: Record<string, number>;
}

export interface BatchSimulationResponse {
	simulation_id: string;
	mode: string;
	total_records: number;
	target: StrategyAggregate;
	active: StrategyAggregate | null;
	decision_shifts: { from_decision: string; to_decision: string; count: number }[];
	segment_impact: {
		segment: string;
		total: number;
		target_decision_counts: Record<string, number>;
		active_decision_counts: Record<string, number> | null;
	}[];
}

export interface ManualReviewCase {
	case_id: string;
	application_id: string;
	product_type: string;
	channel: string;
	system_decision: string;
	system_reason_codes: string[];
	status: string;
	priority: string;
	assigned_to: string | null;
	sla_due_at: string | null;
	sla_breached: boolean;
	created_at: string;
}

export interface CaseComment {
	id: string;
	author_label: string;
	body: string;
	created_at: string;
}

export interface CaseDocument {
	id: string;
	name: string;
	status: string;
	requested_at: string;
	resolved_at: string | null;
}

export interface CaseDetail extends ManualReviewCase {
	decision_id: string;
	trace_id: string | null;
	risk_grade: string | null;
	score: number | null;
	applicant_summary: Record<string, unknown>;
	loan_summary: Record<string, unknown>;
	vehicle_summary: Record<string, unknown>;
	analyst_decision: string | null;
	analyst_decided_by: string | null;
	analyst_decided_at: string | null;
	approved_limit: number | null;
	approved_tenor_months: number | null;
	override_reason_code: string | null;
	override_reason: string | null;
	escalated_to: string | null;
	notes: string;
	comments: CaseComment[];
	documents: CaseDocument[];
	closed_at: string | null;
}

export interface AuditLogItem {
	id: string;
	event_type: string;
	entity_type: string;
	entity_id: string;
	entity_version: string | null;
	action: string;
	actor_type: string;
	actor_label: string;
	reason: string | null;
	before_value: Record<string, unknown> | null;
	after_value: Record<string, unknown> | null;
	metadata: Record<string, unknown>;
	correlation_id: string | null;
	request_id: string | null;
	created_at: string;
}

export interface ApprovalRequest {
	request_id: string;
	entity_type: string;
	entity_id: string;
	entity_version: string | null;
	status: string;
	change_summary: string;
	request_reason: string;
	decision_reason: string | null;
	requested_by: string | null;
	decided_by: string | null;
	decided_at: string | null;
	created_at: string;
}

export interface AdminUser {
	username: string;
	full_name: string;
	actor_type: string;
	is_active: boolean;
	roles: string[];
}

export interface RoleMatrixItem {
	code: string;
	name: string;
	permissions: string[];
}

export interface DecisionSummary {
	total_applications: number;
	approval_rate: number;
	reject_rate: number;
	manual_review_rate: number;
	error_rate: number;
	decision_counts: Record<string, number>;
	top_reason_codes: { code: string; count: number }[];
	api_latency_p95_ms: number | null;
	manual_review_queue_size: number;
}

export interface Feature {
	id: string;
	path: string;
	label: string;
	description: string;
	data_type: string;
	source: string;
	category: string;
	allowed_values: unknown[] | null;
	active: boolean;
	created_at: string | null;
}

export interface RegisteredModel {
	id: string;
	code: string;
	version_label: string;
	name: string;
	provider: string;
	description: string;
	active: boolean;
	metadata: Record<string, unknown>;
	created_at: string | null;
}

export interface DecisionTrendBucket {
	date: string;
	total: number;
	decision_counts: Record<string, number>;
}

export interface DecisionTrend {
	interval: string;
	buckets: DecisionTrendBucket[];
}

export interface Meta {
	features: { path: string; description: string; derived: boolean }[];
	operators: string[];
	decisions: string[];
	product_types: string[];
	rule_categories: string[];
	config_statuses: string[];
	step_types: string[];
	step_on_error: string[];
	case_statuses: string[];
	case_priorities: string[];
	reason_categories: string[];
	reason_severities: string[];
}
