from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_workflow import AgentWorkflowDefinition
from app.schemas.agent_workflow import WorkflowStatus


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(AgentWorkflowDefinition.id).where(
            AgentWorkflowDefinition.slug == "research-assistant"
        )
    )
    if existing is not None:
        return

    session.add(
        AgentWorkflowDefinition(
            slug="research-assistant",
            name="Research assistant",
            description="Plan → search tool → summarize agent chain for demos.",
            status=WorkflowStatus.PUBLISHED.value,
            steps=[
                {
                    "key": "plan",
                    "type": "agent",
                    "prompt_template": "Create a short research plan for: {goal}",
                },
                {
                    "key": "search",
                    "type": "tool",
                    "tool_name": "search",
                    "input_from": "plan_output",
                },
                {
                    "key": "summarize",
                    "type": "agent",
                    "prompt_template": "Summarize findings: {search_output}",
                },
            ],
        )
    )
    await session.commit()
