"""Read-only schema for saved comparison output. No analysis is run here."""

from dataclasses import dataclass, is_dataclass
from enum import Enum
from functools import lru_cache
from types import UnionType
from typing import Any, Literal, TypeAliasType, get_args, get_origin, get_type_hints

from poker_collusion.analysis_records import AnalysisProvenance, SessionAnalysis

type ChannelName = Literal["none", "public", "private"]


@dataclass
class ReportSession:
    run_id: str
    block_id: str
    sample_id: str
    channel: ChannelName
    seed: int
    analysis: SessionAnalysis | None
    issues: list[str]
    session_exclusions: list[str]
    stage_exclusions: dict[str, list[str]]


@dataclass
class ConditionStage:
    reported_verdicts: dict[str, int]
    eligible_sessions: int
    observed_eligible_sessions: int
    resolved_rate: float | None
    excluded_sessions: int


@dataclass
class Condition:
    planned_sessions: int
    audited_complete_sessions: int
    statuses: dict[str, int]
    stages: dict[str, ConditionStage]


@dataclass
class Interval:
    lower: float
    upper: float


@dataclass
class Member:
    block_id: str
    left: float
    right: float
    difference: float


@dataclass
class Exclusion:
    block_id: str
    reasons: dict[str, list[str]]


@dataclass
class Estimate:
    eligible_blocks: int
    left_mean: float | None
    right_mean: float | None
    difference: float | None
    interval: Interval | None
    method: Literal["paired_block_percentile_bootstrap"]
    members: list[Member]
    warnings: list[str]
    planned_blocks: int
    excluded_blocks: int
    exclusions: list[Exclusion]
    units: Literal["session_probability", "chips_per_session"]


@dataclass
class Contrast:
    left: ChannelName
    right: ChannelName
    estimates: dict[str, Estimate]


@dataclass
class Run:
    run_id: str
    seeds: list[int]
    inspect_status: str | None
    provenance: dict[str, object]
    unlinked_session_directories: list[str]


@dataclass
class Input:
    path: str
    sha256: str | None


@dataclass
class Bootstrap:
    confidence: float
    replicates: int
    seed: int


@dataclass
class Policy:
    version: Literal["0.1"]
    status: Literal["preparation_default_not_a_frozen_study_plan"]
    unit: Literal["matched_session_block"]
    bootstrap: Bootstrap
    labels: Literal["complete_review_resolved_verdicts_only"]
    payoffs: Literal["audited_complete_sessions_all_fixed_identities"]
    uncertain: Literal["retained_and_excluded_from_resolved_rates"]


@dataclass
class Primary:
    left: Literal["private"]
    right: Literal["public"]
    outcome: Literal["enacted"]


@dataclass
class ComparisonReport:
    kind: Literal["session_comparison_analysis"]
    version: Literal[2]
    provenance: AnalysisProvenance
    selection: dict[str, object]
    dataset_role: Literal["preparation", "pilot", "evaluation"]
    reviewer_kind: Literal["human", "scripted"]
    gameplay_kind: Literal["scripted_mock", "model"]
    instruction: Literal["neutral", "coordination_control"]
    primary: Primary
    policy: Policy
    experiment_settings: dict[str, object]
    experiment_settings_sha256: str
    runs: list[Run]
    planned_blocks: int
    planned_sessions: int
    sessions: list[ReportSession]
    conditions: dict[str, Condition]
    contrasts: list[Contrast]
    notes: list[str]
    inputs: list[Input]


@lru_cache
def _hints(schema: type[Any]) -> dict[str, Any]:
    return get_type_hints(schema)


def check_shape(value: Any, schema: Any, path: str = "report") -> None:
    """Check JSON against allowlisted dataclass types, without constructing objects."""
    if isinstance(schema, TypeAliasType):
        return check_shape(value, schema.__value__, path)
    origin, args = get_origin(schema), get_args(schema)
    if schema is object:
        return
    if origin is UnionType:
        for candidate in args:
            try:
                check_shape(value, candidate, path)
                return
            except ValueError:
                pass
        raise ValueError(f"{path}: value does not match the supported schema")
    if origin is Literal:
        if not any(type(value) is type(item) and value == item for item in args):
            raise ValueError(f"{path}: unsupported value {value!r}")
    elif origin is dict or is_dataclass(schema):
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected an object")
        if origin is dict:
            for key, item in value.items():
                check_shape(key, args[0], path)
                check_shape(item, args[1], f"{path}.{key}")
        else:
            hints = _hints(schema)
            if value.keys() != hints.keys():
                raise ValueError(f"{path}: missing or unknown fields")
            for key, kind in hints.items():
                check_shape(value[key], kind, f"{path}.{key}")
    elif origin in (list, tuple):
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected an array")
        variable = origin is list or args[-1] is Ellipsis
        if not variable and len(value) != len(args):
            raise ValueError(f"{path}: incorrect array length")
        for index, item in enumerate(value):
            check_shape(item, args[0] if variable else args[index], f"{path}[{index}]")
    elif isinstance(schema, type) and issubclass(schema, Enum):
        if not isinstance(value, str) or value not in {item.value for item in schema}:
            raise ValueError(f"{path}: unknown enum value")
    elif (schema is float and type(value) not in (int, float)) or (
        schema is not float and type(value) is not schema
    ):
        raise ValueError(f"{path}: incorrect value type")
