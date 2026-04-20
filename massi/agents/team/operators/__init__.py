import json
from abc import ABC, abstractmethod

from langchain.chat_models import BaseChatModel

from massi.agents.team._dto import (
    MetadataGapTask,
    MetadataGapTaskOutcome,
    VerifiedMetadataGapTask,
    XMLBlueprintGapPattern,
)
from massi.agents.team.operators.data_explorer import (
    DataExplorerAgent,
    DataExplorerRequest,
    DataExplorerResponse,
)

# Agent Protocol
# --------------


class GapDerivationOperator(ABC):
    @abstractmethod
    def invoke(
        self,
        prompt: str,
        task: MetadataGapTask,
    ) -> MetadataGapTaskOutcome: ...


# Agent Instances
# ---------------


class DataGapDervationOperator(GapDerivationOperator):
    def __init__(
        self, llm_client: BaseChatModel, recursion_limit: int = 25, turn_limit: int = 7
    ):
        self._agent = DataExplorerAgent(
            {
                "llm_client": llm_client,
                "recursion_limit": recursion_limit,
                "turn_limit": turn_limit,
            }
        )

    def invoke(
        self,
        prompt: str,
        task: VerifiedMetadataGapTask,
    ) -> MetadataGapTaskOutcome:
        request: DataExplorerRequest = {
            "instruction": prompt,
            "plaintext_files": task["gap_scope_plaintext_files"],
            "tabular_files": task["gap_scope_tabular_files"],
        }
        response: DataExplorerResponse = self._agent.invoke(request)["final_output"]

        if response["result_value"]:
            result = response["result_value"]
        else:
            result = json.dumps(
                XMLBlueprintGapPattern.get_gap_pattern(
                    task["gap_id"],
                    f'{task["gap_type"]}-{response["success"]=}-{response["status"]=}',
                    {response["outcome"]},
                )
            )
        return {"result": {"content": result}, "task": task}
