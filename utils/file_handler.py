"""RAG 项目的文件处理工具。"""

import hashlib
import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from utils.logger_handler import logger
from utils.path_tool import get_abs_path


_READ_CHUNK_SIZE = 4096


def get_file_md5_hex(file_path: str) -> str:
    """计算文件的 MD5 十六进制摘要。

    文件会被分块读取，避免大文件一次性加载到内存。

    :param file_path: 文件路径，相对路径以项目根目录为基准。
    :return: 文件的 MD5 十六进制字符串。
    :raises OSError: 文件不存在或无法读取时抛出。
    """
    absolute_path = (
        file_path if os.path.isabs(file_path) else get_abs_path(file_path)
    )

    try:
        md5_hash = hashlib.md5()
        with open(absolute_path, "rb") as file:
            while chunk := file.read(_READ_CHUNK_SIZE):
                md5_hash.update(chunk)

        md5_hex = md5_hash.hexdigest()
        logger.info("Calculated MD5 for file: %s", absolute_path)
        return md5_hex
    except Exception:
        logger.exception("Failed to calculate MD5 for file: %s", absolute_path)
        raise


def listdir_with_allowed_type(
    directory: str,
    allowed_suffix: tuple[str, ...],
) -> list[str]:
    """列出目录下所有符合指定后缀的文件。

    仅检查目录的直接子文件，不会递归扫描子目录；后缀匹配
    不区分大小写。

    :param directory: 要扫描的目录，相对路径以项目根目录为基准。
    :param allowed_suffix: 允许的文件后缀，例如 ``(".pdf", ".txt")``。
    :return: 按文件名排序的绝对路径列表。
    :raises OSError: 目录不存在或无法读取时抛出。
    """
    absolute_directory = (
        directory if os.path.isabs(directory) else get_abs_path(directory)
    )
    normalized_suffix = tuple(suffix.lower() for suffix in allowed_suffix)

    try:
        with os.scandir(absolute_directory) as entries:
            matched_files = [
                os.path.abspath(entry.path)
                for entry in entries
                if entry.is_file()
                and entry.name.lower().endswith(normalized_suffix)
            ]

        matched_files.sort(
            key=lambda path: os.path.basename(path).casefold(),
        )
        logger.info(
            "Found %d allowed file(s) in directory: %s",
            len(matched_files),
            absolute_directory,
        )
        return matched_files
    except Exception:
        logger.exception("Failed to list directory: %s", absolute_directory)
        raise


def pdf_loader(file_path: str) -> list[Document]:
    """使用 LangChain ``PyPDFLoader`` 加载 PDF 文件。

    :param file_path: PDF 文件路径，相对路径以项目根目录为基准。
    :return: 按页加载的 LangChain Document 列表。
    :raises Exception: PDF 文件加载失败时抛出。
    """
    absolute_path = (
        file_path if os.path.isabs(file_path) else get_abs_path(file_path)
    )

    try:
        documents = PyPDFLoader(absolute_path).load()
        logger.info(
            "Loaded PDF file with %d document(s): %s",
            len(documents),
            absolute_path,
        )
        return documents
    except Exception:
        logger.exception("Failed to load PDF file: %s", absolute_path)
        raise


def txt_loader(file_path: str) -> list[Document]:
    """使用 LangChain ``TextLoader`` 以 UTF-8 编码加载文本文件。

    :param file_path: 文本文件路径，相对路径以项目根目录为基准。
    :return: LangChain Document 列表。
    :raises Exception: 文本文件加载失败时抛出。
    """
    absolute_path = (
        file_path if os.path.isabs(file_path) else get_abs_path(file_path)
    )

    try:
        documents = TextLoader(absolute_path, encoding="utf-8").load()
        logger.info(
            "Loaded text file with %d document(s): %s",
            len(documents),
            absolute_path,
        )
        return documents
    except Exception:
        logger.exception("Failed to load text file: %s", absolute_path)
        raise
