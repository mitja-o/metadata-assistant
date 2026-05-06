from pathlib import Path
from time import time
from typing import Any, Self, TypedDict
import pandas as pd

# Experiment Scenario Loading
# ---------------------------

# Scenario Constructs
# ===================


class ScenarioConfig(TypedDict, total=False):
    core_platform: str
    core_llm: str
    proxy_platform: str
    embedding_model: str
    rag_llm: str


class ScenarioSpec(TypedDict, total=False):
    # -- computed identifier
    scenario_tag: str
    # -- provided spec details
    idx: int
    variant: str
    schema: str
    strategy: str
    provider: str
    config: ScenarioConfig


class DataCase(TypedDict, total=False):
    # -- computed identifier
    case_tag: str
    # -- provided case details
    # FIXME: replace with actual GBIF case
    source_value: str
    # --- case logging details
    success: bool = True
    cause: str = ""
    error: str = ""
    timestamp: float | None = None


class ScenarioXCase(ScenarioSpec, DataCase): ...


type Scenario = tuple[int, ScenarioXCase]


# Scenario Loading and Logging
# ============================


def get_scenario_csv_path() -> Path:
    return Path("./_evaluation/runtime/experiment_scenarios.csv")


def get_cases_csv_path() -> Path:
    return Path("./_evaluation/runtime/experiment_cases.csv")


def get_scenario_x_case_log_csv_path() -> Path:
    return Path("./_evaluation/runtime/experiment_cross_scenarios_cases.log.csv")


def make_scenario_tag(idx: Any, spec: ScenarioSpec) -> str:
    return f"s_{idx}-{spec['variant']}-{spec['schema']}-{spec['schema']}-{spec['provider']}-{spec['config']}"


def make_case_tag(scenario_tag: str, case_id: int) -> str:
    return f"c_{case_id}-x-{scenario_tag}"


def load_scenarios_x_cases(
    scenario_query: ScenarioSpec,
    case_head_limit: int | None = None,
) -> list[Scenario]:
    scenarios_csv = get_scenario_csv_path()
    cases_csv = get_cases_csv_path()
    scenario_x_case_log_csv = get_scenario_x_case_log_csv_path()

    scenarios = pd.read_csv(scenarios_csv)
    cases = pd.read_csv(cases_csv)
    scenario_x_case_log = (
        pd.read_csv(scenario_x_case_log_csv)
        if scenario_x_case_log_csv.exists()
        else None
    )

    # -- select scenarios
    selected_scenarios = scenarios[
        scenarios.apply(
            lambda s: all([s[qk] == qv for qk, qv in scenario_query.items()]), axis=1
        )
    ]

    # -- select cases
    selected_cases = cases if case_head_limit is None else cases.head(case_head_limit)
    selected_cases["case_id"] = selected_cases.index

    # -- generate selected scenario x case entries
    cross_scenario_cases = selected_scenarios.merge(selected_cases, how="cross")
    cross_scenario_cases["scenario_tag"] = cross_scenario_cases.apply(
        lambda r: make_scenario_tag(r.name, r), axis=1
    )
    cross_scenario_cases["case_tag"] = cross_scenario_cases.apply(
        lambda r: make_case_tag(r["scenario_tag"], r["case_id"]), axis=1
    )

    # -- filter out the logged scenario x case entries
    logged_case_tags = scenario_x_case_log["case_tag"].tolist()
    remaining_sources = (
        cross_scenario_cases
        if not scenario_x_case_log_csv.exists()
        else cross_scenario_cases[
            cross_scenario_cases["case_tag"].apply(lambda t: t not in logged_case_tags)
        ]
    )

    return [(i, r.to_dict()) for i, r in remaining_sources.iterrows()]


def build_log_entry(
    scenario_x_case: ScenarioXCase, success: bool = True, error: Exception | None = None
) -> pd.DataFrame:
    return pd.DataFrame.from_records(
        [
            {
                **scenario_x_case,
                "success": success,
                "cause": "error" if error else ("" if success else "unknown-failure"),
                "error": str(error) if error else "",
                "timestamp": time(),
            }
        ]
    )


# Scenario Suites
# ===============


class ScenarioBasedSuite:
    scenarios_x_cases: list[Scenario]


class MetaScenarioSuite:
    cls: type[ScenarioBasedSuite]


def pytest_generate_tests(metafunc: MetaScenarioSuite):
    """A Pytest hook that parametrises the test suite from the loaded scenarios.

    Args:
        metafunc (n/a): the test function picked up by pytest
    """
    run_ids = []
    input_arguments = []
    input_values = []
    for id, scenario_x_case in metafunc.cls.scenarios_x_cases:
        input_arguments = ["id", "scenario_x_case"]
        input_values.append(
            (
                id,
                scenario_x_case,
            )
        )
        run_ids.append(scenario_x_case["case_tag"])
    metafunc.parametrize(input_arguments, input_values, ids=run_ids, scope="class")


# Test Suites
# -----------


class TestSampleWithScenarios(ScenarioBasedSuite):
    scenarios_x_cases = load_scenarios_x_cases(
        {
            "variant": "full",
            "provider": "openai-platform",
            "schema": "dwc",
        },
        case_head_limit=10,
    )

    def test_demo1(self, id, scenario_x_case):
        test_record = ScenarioXCase(**scenario_x_case)
        log_csv = get_scenario_x_case_log_csv_path()
        log_exists = Path(log_csv).exists()

        try:
            assert test_record["source_value"] == "OK"

            build_log_entry(test_record).to_csv(
                log_csv, mode="a", index=False, header=not log_exists
            )
        except Exception as e:
            build_log_entry(test_record, success=False, error=e).to_csv(
                log_csv, mode="a", index=False, header=not log_exists
            )
            raise e
