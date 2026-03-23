from contextlib import contextmanager
import json
import os
import pathlib
from time import perf_counter, time
from typing import Callable, Generator
import random

from dotenv import load_dotenv
from lmnr import Laminar, observe
import pytest
import pandas as pd

from massi._experiments.author_agent import AuthorAgentProxyPrompt, create_author_agent
from massi.agents.interfaces import Config, Dependencies
from massi.agents.massi import MassiScenarioFactory, create_ollama_llm


@contextmanager
def timeit() -> Generator[Callable[[], float]]:
    t1 = t2 = perf_counter()
    yield lambda: t2 - t1
    t2 = perf_counter()


def evaluation_id(key: str) -> str:
    return f"evaluation-{key}-{time()}"


class Defaults:
    # WARN: this evaluation script should be run from the project's root directory

    evaluation_db = "./_evaluation/reports/reports.duck.db"
    evaluation_csv_tmpl = "./_evaluation/reports/reports.{key}.csv"

    input_paper = (
        "./_evaluation/papers/p1-a-geospatial-and-binomial-logistic-regression.pdf"
    )

    massi_config = Config(
        **{
            "model_url": "http://0.0.0.0:11434",
            "model_name": "granite4:3b",
        }
    )

    author_agent_configs = {
        "embedding": Config(
            **{
                "model_url": "http://0.0.0.0:11434",
                "model_name": "qwen3-embedding:0.6b",
            }
        ),
        "chat": Config(
            **{
                "model_url": "http://0.0.0.0:11434",
                "model_name": "lfm2.5-thinking:latest",
            }
        ),
    }

    input_base_metadata = {
        "entry_version": 1,
        "entry_id": "KY PFAS Paper",
        "description": 'Data used for the paper titled "A geospatial and binomial logistic regression model to prioritize sampling for per- and polyfluorinated alkyl substances in public water systems". DOI: https://doi.org/10.1002/ieam.4614',
        "products": [
            "Map 1 Potential hot-spot map",
            "US map",
            "Model_says_NO",
            "Model_says_yes",
            "hot-spot_map",
            "other/gis_distance_matrix.py",
        ],
    }
    """Taken from <https://github.com/MoseleyBioinformaticsLab/miagis/blob/main/examples/Paper_1/base_metadata.json>"""


def mask_keys(metadata: dict[str, any], excluded_keys: list[str]):
    return {k: v for k, v in metadata.items() if k not in excluded_keys}


def write_metadata(path: pathlib.Path | str, metadata: dict[str, any]) -> pathlib.Path:
    clean_path = pathlib.Path(path)
    with open(clean_path, "w") as bmf:
        json.dump(metadata, bmf)
    return clean_path


@pytest.fixture()
def base_metadata_file_name(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "base_metadata.json"
    return fn


@pytest.fixture()
def laminar_observer():
    load_dotenv()
    Laminar.initialize(
        base_url="http://0.0.0.0",
        project_api_key=os.environ["LMNR_PROJECT_API_KEY"],
        http_port=int(os.environ["LMNR_PROJECT_HTTP_PORT"]),
        grpc_port=int(os.environ["LMNR_PROJECT_GRPC_PORT"]),
    )


@pytest.fixture()
def author_proxy():
    author_proxy, _ = create_author_agent(
        Defaults.input_paper,
        Defaults.author_agent_configs["embedding"],
        Defaults.author_agent_configs["chat"],
    )
    proxy_prompt_client = AuthorAgentProxyPrompt(author_proxy)
    return proxy_prompt_client


@observe(span_type="LLM", session_id=evaluation_id("evaluation-run"))
def test_empty_metadata(base_metadata_file_name, laminar_observer, author_proxy):
    # --- Arrange ---
    eval_id = evaluation_id(test_empty_metadata.__name__)
    thread_config = {"configurable": {"thread_id": str(random.randint(1, 100))}}

    og_metadata = Defaults.input_base_metadata
    metadata = mask_keys(og_metadata, og_metadata.keys())
    metadata_path = write_metadata(base_metadata_file_name, metadata)

    print(metadata)
    print(metadata_path)
    assert not metadata.keys() == og_metadata.keys(), "Keys should be masked!"

    deps = Dependencies(
        llm_client=create_ollama_llm(Defaults.massi_config),
        prompt_client=author_proxy,
        working_directory=str(metadata_path.parent),
    )

    factory = MassiScenarioFactory(Defaults.massi_config)
    graph, _ = factory.base_metadata_graph(dependencies=deps)

    # --- Act ---
    with timeit() as timer:
        graph.invoke({}, thread_config)

    state = graph.get_state(thread_config)
    print(f"{state.next=}")
    print(f"{state.values=}")

    # --- Assert ---
    execution_time = timer()
    updated_metadata = graph.get_state(thread_config).values["updated_metadata"][
        "metadata"
    ]
    query_plan = graph.get_state(thread_config).values["query_plan"]

    # FIXME(use a dataclass / typed dict / pydantic model): make the evaluation recording type safe
    pd.DataFrame.from_records(
        [
            dict(
                evaluation_id=eval_id,
                execution_time_seconds=execution_time,
                original_metadata=og_metadata,
                masked_metadata=metadata,
                produced_metadata=updated_metadata,
                query_plan=query_plan,
            )
        ]
    ).to_csv(Defaults.evaluation_csv_tmpl.format(key=eval_id))

    for k, v in og_metadata.items():
        assertion_error = f"Expected value for key: {k}; original value: {v}; current value: {updated_metadata.get(k)}"
        assert updated_metadata[k], assertion_error
