from typing import Any

from app.core.exceptions import AppError
from app.schemas.agent_workflow import RunStatus, StepStatus, StepType, WorkflowStep


def _resolve_input(step: WorkflowStep, context: dict[str, Any]) -> Any:
    if step.input_from:
        if step.input_from not in context:
            raise AppError(f"Missing context key {step.input_from!r} for step {step.key!r}")
        return context[step.input_from]
    if not context:
        return ""
    last_key = next(reversed(context))
    return context[last_key]


def _render_prompt(template: str, context: dict[str, Any], run_input: dict[str, Any]) -> str:
    merged = {**run_input, **context}
    try:
        return template.format(**merged)
    except KeyError as exc:
        raise AppError(f"Prompt template missing variable: {exc}") from exc


def _mock_tool(tool_name: str, tool_input: Any) -> dict[str, Any]:
    text = str(tool_input)
    if tool_name == "search":
        return {"results": [f"result-for:{text[:80]}"]}
    if tool_name == "calculator":
        return {"expression": text, "value": len(text)}
    return {"tool": tool_name, "echo": text}


def execute_steps(
    *,
    steps: list[dict[str, Any]],
    run_input: dict[str, Any],
) -> tuple[RunStatus, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Run agent/tool steps synchronously; returns context, output, and step logs."""
    parsed = [WorkflowStep.model_validate(raw) for raw in steps]
    context: dict[str, Any] = dict(run_input)
    logs: list[dict[str, Any]] = []

    for index, step in enumerate(parsed):
        step_input = _resolve_input(step, context)
        log_input = {"value": step_input}
        try:
            if step.type == StepType.AGENT:
                prompt = _render_prompt(step.prompt_template or "", context, run_input)
                output = f"agent:{prompt[:500]}"
            else:
                output = _mock_tool(step.tool_name or "noop", step_input)
            context_key = f"{step.key}_output"
            context[context_key] = output
            logs.append(
                {
                    "sequence": index,
                    "step_key": step.key,
                    "step_type": step.type.value,
                    "status": StepStatus.COMPLETED.value,
                    "input_payload": log_input,
                    "output_payload": {"value": output},
                }
            )
        except AppError as exc:
            logs.append(
                {
                    "sequence": index,
                    "step_key": step.key,
                    "step_type": step.type.value,
                    "status": StepStatus.FAILED.value,
                    "input_payload": log_input,
                    "output_payload": {"error": exc.message},
                }
            )
            return RunStatus.FAILED, {}, context, logs

    final_output = context.get(f"{parsed[-1].key}_output", context)
    return RunStatus.COMPLETED, {"result": final_output}, context, logs
