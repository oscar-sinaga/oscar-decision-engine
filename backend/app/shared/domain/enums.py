"""Domain enums shared across modules (docs/06 §4)."""

from enum import StrEnum


class DecisionType(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    APPROVE_WITH_CONDITION = "APPROVE_WITH_CONDITION"
    REQUEST_ADDITIONAL_DOCUMENT = "REQUEST_ADDITIONAL_DOCUMENT"
    FRAUD_INVESTIGATION = "FRAUD_INVESTIGATION"
    ERROR = "ERROR"


# Most severe first; strategy execution aggregates candidate decisions by
# taking the most severe one. This ordering is engine mechanics, not policy.
DECISION_SEVERITY: tuple[DecisionType, ...] = (
    DecisionType.ERROR,
    DecisionType.FRAUD_INVESTIGATION,
    DecisionType.REJECT,
    DecisionType.MANUAL_REVIEW,
    DecisionType.REQUEST_ADDITIONAL_DOCUMENT,
    DecisionType.APPROVE_WITH_CONDITION,
    DecisionType.APPROVE,
)


class ProductType(StrEnum):
    MOTOR_LEASEBACK = "MOTOR_LEASEBACK"
    CAR_LEASEBACK = "CAR_LEASEBACK"
    AUTO_LOAN_MOTOR = "AUTO_LOAN_MOTOR"
    AUTO_LOAN_CAR = "AUTO_LOAN_CAR"
    MULTIPURPOSE_LOAN = "MULTIPURPOSE_LOAN"
    TOP_UP = "TOP_UP"


class ApplicationStatus(StrEnum):
    RECEIVED = "RECEIVED"
    DECIDED = "DECIDED"
    PENDING_REVIEW = "PENDING_REVIEW"
    ERROR = "ERROR"


class ExecutionMode(StrEnum):
    PRODUCTION = "PRODUCTION"
    SIMULATION = "SIMULATION"


class ConfigStatus(StrEnum):
    """Lifecycle of versioned configuration (rules, strategies, tables, scorecards)."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"


class RuleCategory(StrEnum):
    VALIDATION = "VALIDATION"
    ELIGIBILITY = "ELIGIBILITY"
    AFFORDABILITY = "AFFORDABILITY"
    BUREAU = "BUREAU"
    FRAUD = "FRAUD"
    COLLATERAL = "COLLATERAL"
    LIMIT = "LIMIT"
    TENOR = "TENOR"
    PRICING = "PRICING"
    ROUTING = "ROUTING"
    FINAL_DECISION = "FINAL_DECISION"


class StepType(StrEnum):
    VALIDATION = "VALIDATION"
    RULE_SET = "RULE_SET"
    DECISION_TABLE = "DECISION_TABLE"
    SCORECARD = "SCORECARD"
    CALCULATION = "CALCULATION"
    OUTPUT = "OUTPUT"


class StepOnError(StrEnum):
    FAIL = "FAIL"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    CONTINUE = "CONTINUE"


class StepStatus(StrEnum):
    PASSED = "PASSED"
    TRIGGERED = "TRIGGERED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ReasonCodeCategory(StrEnum):
    VALIDATION = "VALIDATION"
    ELIGIBILITY = "ELIGIBILITY"
    AFFORDABILITY = "AFFORDABILITY"
    BUREAU = "BUREAU"
    FRAUD = "FRAUD"
    COLLATERAL = "COLLATERAL"
    LIMIT = "LIMIT"
    OPERATIONAL = "OPERATIONAL"


class ReasonSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    DECLINE = "DECLINE"
    REVIEW = "REVIEW"


class CaseStatus(StrEnum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    PENDING_DOCUMENTS = "PENDING_DOCUMENTS"
    ESCALATED = "ESCALATED"
    APPROVED_BY_ANALYST = "APPROVED_BY_ANALYST"
    REJECTED_BY_ANALYST = "REJECTED_BY_ANALYST"
    CLOSED = "CLOSED"


class CasePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    API_CLIENT = "API_CLIENT"


class SimulationType(StrEnum):
    SINGLE = "SINGLE"
    BATCH = "BATCH"


class SimulationStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class FeatureDataType(StrEnum):
    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"


class FeatureSource(StrEnum):
    """Where a catalog feature's value originates."""

    PAYLOAD = "PAYLOAD"  # supplied on the application payload
    DERIVED = "DERIVED"  # computed by a CALCULATION step
    SCORE = "SCORE"  # produced by a SCORECARD step
