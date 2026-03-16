from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TypedDict

from langchain.chat_models import BaseChatModel
from langchain.messages import HumanMessage
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from massi.agents.interfaces import Config, PromptClient

# Workflow State
# --------------


class AuthorAgentState(TypedDict):
    paper_summary: str
    question: str
    context: str
    answer: str


@dataclass
class Dependencies:
    llm_client: BaseChatModel
    retriever: BaseRetriever
    document_chunks: list[Document]


# Workflow Nodes
# --------------
# TODO: consider adding an extra node to produce a paper summary for extended context.


def retrieve_content(state: AuthorAgentState, deps: Dependencies) -> AuthorAgentState:
    """Find relevant text in the PDF."""
    docs = deps.retriever.invoke(state["question"])
    context = "\n\n".join(doc.page_content for doc in docs)
    return {"context": context}


def generate_response(state: AuthorAgentState, deps: Dependencies) -> AuthorAgentState:
    """Generate response in the author's persona."""
    content = f"Context: {state['context']}\n\nQuestion: {state['question']}"
    response = deps.llm_client.invoke([HumanMessage(content=content)])
    return {"answer": response.content}


# System Construction
# -------------------


def load_document_chunks(pdf_path: Path) -> list[Document]:
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(docs)


def setup_author_proxy_components(
    document_chunks: list[Document], embedding_config: Config, chat_config: Config
) -> Dependencies:
    embeddings = OllamaEmbeddings(
        model=embedding_config.model_name, base_url=embedding_config.model_url
    )
    vectorstore = InMemoryVectorStore.from_documents(document_chunks, embeddings)
    retriever = vectorstore.as_retriever()

    author_system_msg = (
        "You are the author of the provided document that describes your scientific work. "
        "This work has lead to a publication of a dataset for future scientific reuse. "
        "A data steward will ask you questions aimed at producing metadata for your dataset. "
        "Answer using ONLY the context provided. If the answer isn't there, state that you haven't written about it. "
        "Tone: Professional."
    )
    llm = ChatOllama(
        model=chat_config.model_name,
        base_url=chat_config.model_url,
        temperature=0.3,
        system=author_system_msg,
    )

    return Dependencies(llm, retriever, document_chunks)


def build_author_workflow(deps: Dependencies):
    workflow = StateGraph(AuthorAgentState)

    workflow.add_node(retrieve_content.__name__, partial(retrieve_content, deps=deps))
    workflow.add_node(generate_response.__name__, partial(generate_response, deps=deps))

    workflow.add_edge(START, retrieve_content.__name__)
    workflow.add_edge(retrieve_content.__name__, generate_response.__name__)
    workflow.add_edge(generate_response.__name__, END)

    return workflow.compile()


# Agent entrypoints
# -----------------

type AuthorAgent = CompiledStateGraph[
    AuthorAgentState, None, AuthorAgentState, AuthorAgentState
]


def create_author_agent(pdf_path: Path, embedding_config: Config, chat_config: Config):
    document_chunks = load_document_chunks(pdf_path)
    deps = setup_author_proxy_components(document_chunks, embedding_config, chat_config)
    return build_author_workflow(deps), deps


class AuthorAgentProxyPrompt(PromptClient):
    def __init__(self, agent: AuthorAgent):
        self.agent = agent

    def prompt_user(
        self, queries: list[str] = [], prelude: list[str] = []
    ) -> list[str]:
        questions = [f"{'.'.join(prelude)}: {q}" "" for q in queries]
        return [self.agent.invoke({"question": q})["answer"] for q in questions]
