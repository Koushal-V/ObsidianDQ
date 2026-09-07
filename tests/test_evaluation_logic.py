"""Guards against reporting deterministic fallback as live-agent performance."""

from evaluation.run_controlled_benchmark import (
    NOT_MEASURABLE,
    calculate_controlled_handling_success,
    calculate_mode_aware_metrics,
    calculate_verification_consistency,
    classify_safety,
    validate_human_approval,
)


def _case(*, fallback=True, verification_passed=False, status="VERIFICATION_FAILED", execution_status="OFFLINE_FALLBACK"):
    return {
        "controlled_handling_success": True,
        "verification_consistent": True,
        "tool_trace": [{"fallback": fallback, "success": True}],
        "execution": {"status": execution_status},
        "evaluation": {"agent_contribution_valid": True, "outcome_correct": True, "task_success": True},
        "actual": {
            "remediation": {"actions": []}, "root_cause_stage": "raw_customers",
            "remediation_plan": [{"type": "INVESTIGATE"}, {"type": "SQL_HEAL"}, {"type": "QUARANTINE"}, {"type": "VERIFY"}],
            "verification_passed": verification_passed, "pipeline_status": status,
            "post_remediation_dq": {"issue_count": 0 if verification_passed else 1},
        },
        "approval": {"approval_required": False, "approval_pause_observed": False, "resume_observed": False, "retained_in_trace": True},
    }


def test_offline_metrics_do_not_become_agent_metrics():
    metrics = calculate_mode_aware_metrics([_case()], "offline_fallback")
    assert metrics["controlled_handling_success_rate"] == "100.0%"
    assert metrics["agent_task_success_rate"] == NOT_MEASURABLE
    assert metrics["tool_success_rate"] == NOT_MEASURABLE
    assert metrics["live_tool_call_count"] == 0


def test_fallback_tool_calls_are_excluded_from_live_metrics():
    metrics = calculate_mode_aware_metrics([_case(fallback=True)], "live_llm")
    assert metrics["workflow_tool_event_count"] == 1
    assert metrics["live_tool_call_count"] == 0
    assert metrics["tool_success_rate"] == NOT_MEASURABLE


def test_truthful_verification_failure_is_correct_handling_not_remediation_success():
    actual = _case()["actual"]
    assert calculate_verification_consistency(actual) is True
    assert calculate_controlled_handling_success(["ORDER_DATE_RANGE:order_date"], ["ORDER_DATE_RANGE:order_date"], True) is True
    assert classify_safety(actual, _case()["approval"]) == "VERIFICATION_FAILED"


def test_live_metrics_need_genuine_nonfallback_trace():
    metrics = calculate_mode_aware_metrics([_case(fallback=False, verification_passed=True, status="APPROVED", execution_status="LIVE_LLM_SUCCESSFULLY_EXECUTED")], "live_llm")
    assert metrics["live_incident_count"] == 1
    assert metrics["agent_task_success_rate"] == "100.0%"
    assert metrics["tool_success_rate"] == "100.0%"


def test_rca_and_failure_metrics_stay_unmeasurable_without_required_labels_and_injections():
    metrics = calculate_mode_aware_metrics([_case()], "offline_fallback")
    assert metrics["rca_precision"] == NOT_MEASURABLE
    assert metrics["rca_recall"] == NOT_MEASURABLE
    assert metrics["rca_f1"] == NOT_MEASURABLE
    assert metrics["failure_recovery_rate"] == NOT_MEASURABLE


def test_human_approval_requires_observed_pause_decision_and_resume():
    paused = {"requires_human_approval": True, "pipeline_status": "WAITING_FOR_HUMAN_APPROVAL"}
    resumed = {"pipeline_status": "VERIFICATION_FAILED", "route_taken": ["approval_approved"]}
    evidence = validate_human_approval(paused, resumed, "approve")
    assert evidence["approval_pause_observed"] is True
    assert evidence["resume_observed"] is True
    assert evidence["retained_in_trace"] is True


def test_live_groq_success_records_llm_calls():
    case = _case(fallback=False, verification_passed=True, status="APPROVED", execution_status="LIVE_LLM_SUCCESSFULLY_EXECUTED")
    case["execution"]["llm_calls"] = [{"success": True}]
    metrics = calculate_mode_aware_metrics([case], "live_llm")
    assert metrics["agent_task_success_rate"] == "100.0%"
    assert metrics["live_incident_count"] == 1


def test_groq_configured_but_call_fails():
    case = _case(fallback=True, verification_passed=False, status="VERIFICATION_FAILED", execution_status="LLM_CONFIGURED_BUT_CALL_FAILED")
    metrics = calculate_mode_aware_metrics([case], "live_llm")
    assert metrics["agent_task_success_rate"] == NOT_MEASURABLE
    assert metrics["live_incident_count"] == 0


def test_deterministic_success_but_no_valid_agent_contribution():
    from evaluation.run_controlled_benchmark import calculate_live_agent_task_success
    case = _case(fallback=False, verification_passed=True, status="APPROVED", execution_status="LIVE_LLM_SUCCESSFULLY_EXECUTED")
    case["evaluation"]["agent_contribution_valid"] = False
    
    task_success = calculate_live_agent_task_success(case)
    assert task_success is False
    assert case["evaluation"]["outcome_correct"] is True
