from pathlib import Path
from time import time
from typing import Any, Self, TypedDict
import pandas as pd


def pytest_generate_tests(metafunc):
    ids = []
    values = []
    arguments = []
    for scenario_id, body in metafunc.cls.scenarios:
        test_cases: list[dict[str, Any]] = body["cases"]
        for test_case in test_cases:
            arguments = [name for name, _ in test_case.items()] + ["scenario_id"]
            values.append([value for value in test_case.values()] + [scenario_id])
            ids.append(f"{scenario_id}-{test_case['case_id']}")
    metafunc.parametrize(arguments, values, ids=ids, scope="class")


class ScenarioCase(TypedDict):
    case_id: str
    transform: str
    source_data: str
    expected_result: str
    success: bool = True
    cause: str = ""
    error: str = ""
    timestamp: float | None = None

    @classmethod
    def build(
        cls,
        case_id: str,
        transform: str,
        source_data: str,
        expected_result: str,
    ) -> Self:
        return cls(
            dict(
                case_id=case_id,
                transform=transform,
                source_data=source_data,
                expected_result=expected_result,
            )
        )


class ScenarioBody:
    cases: list[ScenarioCase]


def get_case_csv_path(key: str) -> Path:
    return Path(f"./_evaluation/runtime/_test_ep_cases_{key}.csv")


def get_log_csv_path(key: str) -> Path:
    return Path(f"./_evaluation/runtime/_test_ep_cases_{key}.log.csv")


def load_scenario(key: str) -> tuple[str, dict[str, ScenarioBody]]:
    case_csv, log_csv = (get_case_csv_path(key), get_log_csv_path(key))

    case_sources, case_log = (
        pd.read_csv(case_csv, index_col="case_id"),
        pd.read_csv(log_csv, index_col="case_id") if log_csv.exists() else None,
    )

    remaining_sources = (
        case_sources
        if not log_csv.exists()
        else case_sources.drop(case_log.index, axis=0)
    )
    test_cases = [
        ScenarioCase(
            {
                c: v
                for c, v in zip(
                    list(remaining_sources.columns) + ["case_id"],
                    row.tolist() + [idx],
                )
            }
        )
        for idx, row in remaining_sources.iterrows()
    ]

    return (key, {"cases": test_cases})


def build_log_entry(
    test_case: ScenarioCase, success: bool = True, error: Exception | None = None
) -> pd.DataFrame:
    return pd.DataFrame.from_records(
        [
            {
                **test_case,
                "success": success,
                "cause": "error" if error else ("" if success else "unknown-failure"),
                "error": str(error) if error else "",
                "timestamp": time(),
            }
        ]
    )


class TestSampleWithScenarios:
    scenarios = [load_scenario("upper")]

    def test_demo1(self, case_id, transform, source_data, expected_result, scenario_id):
        test_case = ScenarioCase.build(case_id, transform, source_data, expected_result)
        log_csv = get_log_csv_path(scenario_id)
        log_exists = Path(log_csv).exists()

        try:
            if transform == "up":
                assert str(source_data).upper() == expected_result
            if transform == "cap":
                assert str(source_data).capitalize() == expected_result

            build_log_entry(test_case).to_csv(
                log_csv, mode="a", index=False, header=not log_exists
            )
        except Exception as e:
            build_log_entry(test_case, success=False, error=e).to_csv(
                log_csv, mode="a", index=False, header=not log_exists
            )
            raise e
