import json
import pathlib

import pytest

from massi._experiments.author_agent import AuthorAgentProxyPrompt, create_author_agent
from massi.agents.interfaces import Config, Dependencies
from massi.agents.massi import MassiScenarioFactory
from langgraph.graph.state import CompiledStateGraph


class Defaults:
    agent_config = Config(
        **{
            "model_url": "http://host.docker.internal:11434",
            "model_name": "granite4:3b",
        }
    )

    input_paper = "./papers/p1-a-geospatial-and-binomial-logistic-regression.pdf"
    author_agent_configs = {
        "embedding": Config(
            **{
                "model_url": "http://host.docker.internal:11434",
                "model_name": "qwen3-embedding:0.6b",
            }
        ),
        "chat": Config(
            **{
                "model_url": "http://host.docker.internal:11434",
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


def stream_until_iterruption(graph: CompiledStateGraph, *args):
    while graph.get_state().next:
        graph.stream()


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


def test_empty_metadata(base_metadata_file_name):
    og_metadata = Defaults.input_base_metadata
    metadata = mask_keys(og_metadata, og_metadata.keys())
    metadata_path = write_metadata(base_metadata_file_name, metadata)

    author_proxy = create_author_agent(
        Defaults.input_paper,
        Defaults.author_agent_configs["embedding"],
        Defaults.author_agent_configs["chat"],
    )
    proxy_prompt_client = AuthorAgentProxyPrompt(author_proxy)

    deps = Dependencies(
        prompt_client=proxy_prompt_client,
        working_directory=str(metadata_path.parent),
    )

    factory = MassiScenarioFactory(Defaults.config)
    graph = factory.base_metadata_graph(dependencies=deps)

    stream_until_iterruption(graph)

    updated_metadata = graph.get_state().values["updated_metadata"]["metadata"]

    for k, v in og_metadata.items():
        assertion_error = f"Expected value for key: {k}; original value: {v}; current value: {updated_metadata.get(k)}"
        assert updated_metadata[k], assertion_error
