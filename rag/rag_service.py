from pathlib import Path
import sys


# 兼容直接执行：python rag/rag_service.py
# 使用 `python -m rag.rag_service` 时，项目根目录本来就在 sys.path 中。
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableLambda

from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_summarize_prompt
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model


def print_prompt(prompt: PromptValue) -> PromptValue:
    """打印填充完成的提示词（其中包含检索到的参考资料）。"""
    print("\n========== 提示词和参考资料 ==========")
    print(prompt.to_string())
    print("======================================\n")
    return prompt


class RagSummarizeService(object):

    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()

        self.prompt_text = load_rag_summarize_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)

        self.model = chat_model

        self.chain = self._init_chain()

    def _init_chain(self):
        chain = (
            self.prompt_template
            | RunnableLambda(print_prompt)
            | self.model
            | StrOutputParser()
        )
        return chain

    def retriever_docs(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    def rag_summarize(self, query: str) -> str:

        context_docs = self.retriever_docs(query)

        context = ""
        counter = 0

        for doc in context_docs:
            counter += 1
            context += (
                f"【参考资料{counter}】：参考资料：{doc.page_content} "
                f"| 参考元数据：{doc.metadata}\n"
            )

        return self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )
if __name__ == '__main__':

    rag = RagSummarizeService()

    print(
        rag.rag_summarize("小户型适合哪些扫地机器人")
    )
