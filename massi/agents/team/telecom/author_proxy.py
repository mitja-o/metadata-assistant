import logging
from abc import ABC, abstractmethod
from functools import partial
from itertools import chain
from pathlib import Path
from typing import Self, TypedDict

from langchain.chat_models import BaseChatModel
from langchain.embeddings import Embeddings
from langchain.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from massi.agents.interfaces import Config

logger = logging.getLogger(__name__)


# Interface
# ---------


class IOAuthorQueryClient(ABC):
    @abstractmethod
    def ask(self, question: str) -> str: ...


# Author Proxy Instances
# ----------------------


# Direct IO with STDIN
# ::::::::::::::::::::


class BasicIOAuthorQueryClient(IOAuthorQueryClient):
    def ask(self, question: str) -> str:
        return input(f"INTERVIEWER: {question}\n>> ")


# RAG Author Proxy
# ::::::::::::::::

# Setup Utilities
# ***************


def create_openai_embeddings(config: Config) -> Embeddings:
    """Creates an OpenAI embedding client.

    Args:
        config (Config): configuration of the embeddings model

    Returns:
        Embeddings: a usable embeddings model client

    Examples:
        >>> from unittest.mock import patch
        >>> sample_config = Config(model_name="text-embedding-3-small", api_key="foo")
        >>> create_openai_embeddings(sample_config) # doctest: +ELLIPSIS
        OpenAIEmbeddings(...)
    """
    assert config.api_key, "API key needs to be specified for OpenAI models"
    return OpenAIEmbeddings(model=config.model_name, api_key=config.api_key)


# Interface
# *********


class RetrieverProps(TypedDict):
    embedder: Embeddings


class GeneratorProps(TypedDict):
    generator: BaseChatModel


class WorkflowProps(GeneratorProps, total=False):
    retriever: VectorStoreRetriever


# Workflow State
# **************


class AuthorAgentState(TypedDict):
    paper_summary: str
    question: str
    context: str
    answer: str


# Prompts
# *******


class PromptBuilder:

    # FIXME(implementation): make the system prompt better phrased and more structured.
    @staticmethod
    def system_prompt() -> str:
        return """
You are the author of the provided document that describes your scientific work. 
This work has lead to a publication of a dataset for future scientific reuse.
A data steward will ask you questions aimed at producing metadata for your dataset.
Answer using ONLY the context provided. If the answer isn't there, state that you haven't written about it.
Tone: Professional.
""".strip()


# Author Proxy Workflow
# *********************
# TODO: consider adding an extra node to produce a paper summary for extended context.


def retrieve_content(
    state: AuthorAgentState, props: WorkflowProps | None = None
) -> AuthorAgentState:
    """Find relevant text in the PDF."""
    assert props
    retriever = props["retriever"]
    assert retriever
    docs = retriever.invoke(state["question"])
    context = "\n\n".join(doc.page_content for doc in docs)
    return {"context": context}


def generate_response(
    state: AuthorAgentState, props: WorkflowProps | None = None
) -> AuthorAgentState:
    """Generate response in the author's persona."""
    assert props
    generator = props["generator"]
    assert generator

    system_prompt = PromptBuilder.system_prompt()
    content = f"Context: {state['context']}\n\nQuestion: {state['question']}"
    response = generator.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=content),
        ]
    )

    return {"answer": response.content}


# Author Proxuy Graph Builder
# ***************************


def build_author_workflow(props: WorkflowProps):
    workflow = StateGraph(AuthorAgentState)

    workflow.add_node(retrieve_content.__name__, partial(retrieve_content, props=props))
    workflow.add_node(
        generate_response.__name__, partial(generate_response, props=props)
    )

    workflow.add_edge(START, retrieve_content.__name__)
    workflow.add_edge(retrieve_content.__name__, generate_response.__name__)
    workflow.add_edge(generate_response.__name__, END)

    return workflow.compile()


type AuthorWorkflow = CompiledStateGraph[
    AuthorAgentState, None, AuthorAgentState, AuthorAgentState
]


# Information Loading
# *******************


def load_document_chunks(pdf_path: Path) -> list[Document]:
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(docs)


def make_retriever(
    documents: list[Document], props: RetrieverProps | None = None
) -> VectorStoreRetriever:
    assert props
    embedder = props["embedder"]
    assert embedder
    vectorstore = InMemoryVectorStore.from_documents(documents, embedder)
    return vectorstore.as_retriever()


# RAG Agent Instance
# ******************


class RagAuthorProxyQueryClient(IOAuthorQueryClient):
    @classmethod
    def build_client(
        cls,
        file_sources: list[Path],
        retriever_props: RetrieverProps,
        generator_props: GeneratorProps,
    ) -> Self:
        all_chunks = list(chain(*(map(load_document_chunks, file_sources))))
        retriever = make_retriever(all_chunks, retriever_props)
        workflow = build_author_workflow({**generator_props, "retriever": retriever})
        return cls(workflow)

    def __init__(self, workflow: AuthorWorkflow):
        self.rag_workflow = workflow

    def ask(self, question: str) -> str:
        return self.rag_workflow.invoke({"question": question})
