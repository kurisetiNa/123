from pathlib import Path
import sys


# 兼容直接执行：python rag/vector_store.py
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.config_handler import chroma_conf
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import (
    pdf_loader,
    txt_loader, 
    listdir_with_allowed_type,
    get_file_md5_hex,
)
from utils.logger_handler import logger

import os



class VectorStoreService:

    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"],
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )
    def get_retriever(self):
        return self.vector_store.as_retriever(
            search_kwargs={"k": chroma_conf.get("k", 3)}
        )



    def load_document(self):



        def check_md5_hex(md5_for_check: str):
            md5_path = get_abs_path(chroma_conf["md5_hex_store"])

            # 如果文件不存在，创建并返回 False
            if not os.path.exists(md5_path):
                open(md5_path, "w", encoding="utf-8").close()
                return False

            # 读取已存在的 md5
            with open(md5_path, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True

            return False


        def save_md5_hex(md5_for_check: str):
            md5_path = get_abs_path(chroma_conf["md5_hex_store"])

            with open(md5_path, "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")


        def get_file_documents(read_path: str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)

            if read_path.endswith("pdf"):
                return pdf_loader(read_path)

            return []
        allowed_files_path: list[str] = listdir_with_allowed_type(
            chroma_conf["data_path"],
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:

            # 获取文件MD5
            md5_hex = get_file_md5_hex(path)

            # 如果已处理过则跳过
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                continue

            try:
                # 读取文件
                documents: list[Document] = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue

                # 文本切分
                split_document: list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue

                # 写入向量数据库
                self.vector_store.add_documents(split_document)

                # 记录MD5，避免重复加载
                save_md5_hex(md5_hex)

                logger.info(f"[加载知识库]{path}内容加载成功")

            except Exception as e:
                logger.error(
                    f"[加载知识库]{path}加载失败: {str(e)}",
                    exc_info=True
                )
                continue


if __name__ == '__main__':

    vs = VectorStoreService()

    vs.load_document()

    retriever = vs.get_retriever()

    res = retriever.invoke("迷路")

    for r in res:
        print(r.page_content)
        print("-" * 20)
