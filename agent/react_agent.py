from pathlib import Path
import sys


# 兼容直接执行：python agent/react_agent.py
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from model.factory import chat_model
from utils.prompt_loader import load_main_prompt
from agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                     get_current_month, fetch_external_data, fill_context_for_report,
                                     has_user_records)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch


class ReactAgent:
    def __init__(self):
        # Checkpointer 按 thread_id 保存每轮消息，让 Agent 能读取之前的对话。
        self.checkpointer = InMemorySaver()
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_main_prompt(),
            tools=[rag_summarize, get_weather, get_user_location, get_user_id,
                   get_current_month, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
            checkpointer=self.checkpointer,
        )

    def execute_stream(
        self,
        query: str,
        thread_id: str = "default",
        user_id: str = "1001",
    ):
        """在指定会话中执行请求，同一 thread_id 会自动延续历史上下文。"""
        report_keywords = ("报告", "使用记录", "清扫记录")
        if any(keyword in query for keyword in report_keywords) and not has_user_records(user_id):
            yield "未找到该用户的相关使用报告\n"
            return

        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }
        config = {"configurable": {"thread_id": thread_id}}

        # 第三个参数context就是上下文runtime中的信息，就是我们做提示词切换的标记
        for chunk in self.agent.stream(
            input_dict,
            config=config,
            stream_mode="values",
            context={"report": False, "user_id": str(user_id)},
        ):
            latest_message = chunk["messages"][-1]
            if isinstance(latest_message, AIMessage) and latest_message.content:
                yield latest_message.content.strip() + "\n"

    def clear_history(self, thread_id: str):
        """删除指定会话在内存中的消息记录。"""
        self.checkpointer.delete_thread(thread_id)


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)
