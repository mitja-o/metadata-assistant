from abc import ABC, abstractmethod
import json

from massi.agents.team._dto import MetadataGapTask, MetadataGapTaskOutcome
from massi.agents.team.operators.data_explorer import (
    DataExplorerAgent,
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
    def __init__(self, llm_client, recursion_limit=25):
        self._agent = DataExplorerAgent(llm_client, recursion_limit=recursion_limit)

    def invoke(self, prompt: str, task: MetadataGapTask) -> MetadataGapTaskOutcome:
        request = {"instruction": prompt, "file_paths": task["gap_scope_files"]}
        response: DataExplorerResponse = self._agent.invoke(request)["final_output"]
        if response["result_value"]:
            result = response["result_value"]
        else:
            result = json.dumps(
                f"{response["success"]=}:{response["status"]}:{response["outcome"]}"
            )
        return {"result": {"content": result}, "task": task}
