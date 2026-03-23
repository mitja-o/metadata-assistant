from massi.agents.constructs import QueryPlan, QueryStep, QueryStepId


def get_next_step(
    plan: QueryPlan, current_step_id: None | QueryStepId = None
) -> None | QueryStep:
    """
    Returns the next step in the plan. If current_step_id is None, returns the first step.

    >>> step1 = QueryStep(id="1", key="a", json_path=".", priority=1, query="q1")
    >>> step2 = QueryStep(id="2", key="b", json_path=".", priority=2, query="q2")
    >>> plan = QueryPlan(queries=[step1, step2])
    >>> get_next_step(plan, None).id
    '1'
    >>> get_next_step(plan, "1").id
    '2'
    >>> get_next_step(plan, "2") is None
    True
    """
    if not current_step_id:
        return plan.queries[0] if plan.queries else None

    # Find the index of the current ID and return the next item if it exists
    indices = (i for i, s in enumerate(plan.queries) if s.id == current_step_id)
    idx = next(indices, None)

    return (
        plan.queries[idx + 1]
        if idx is not None and idx + 1 < len(plan.queries)
        else None
    )


def get_previous_step(
    plan: QueryPlan, current_step_id: QueryStepId
) -> None | QueryStep:
    """
    Returns the step immediately preceding the current_step_id.

    >>> step1 = QueryStep(id="1", key="a", json_path=".", priority=1, query="q1")
    >>> step2 = QueryStep(id="2", key="b", json_path=".", priority=2, query="q2")
    >>> plan = QueryPlan(queries=[step1, step2])
    >>> get_previous_step(plan, "2").id
    '1'
    >>> get_previous_step(plan, "1") is None
    True
    """
    indices = (i for i, s in enumerate(plan.queries) if s.id == current_step_id)
    idx = next(indices, None)

    return plan.queries[idx - 1] if idx is not None and idx > 0 else None


def is_plan_completed(
    plan: QueryPlan, current_step_id: None | QueryStepId = None
) -> bool:
    """
    Checks if the current step is the final leaf of the plan.

    >>> step1 = QueryStep(id="1", key="a", json_path=".", priority=1, query="q1")
    >>> plan = QueryPlan(queries=[step1])
    >>> is_plan_completed(plan, None)
    False
    >>> is_plan_completed(plan, "1")
    True
    >>> is_plan_completed(QueryPlan(queries=[]), None)
    True
    """
    return not plan.queries or (current_step_id == plan.queries[-1].id)
