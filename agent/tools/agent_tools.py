from pathlib import Path
import sys

# 兼容直接执行：python rag/rag_service.py
# 使用 `python -m rag.rag_service` 时，项目根目录本来就在 sys.path 中。
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
from pathlib import Path
import sys


# 兼容直接执行：python agent/tools/agent_tools.py
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from rag.rag_service import RagSummarizeService
from utils.path_tool import get_abs_path

import csv
import random
import re

rag = RagSummarizeService()

month_arr = ["1月", "2月", "3月", "4月", "5月", "6月",
             "7月", "8月", "9月", "10月", "11月", "12月"]


@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)


@tool(description="获取指定城市的天气信息（字符串返回）")
def get_weather(city: str) -> str:
    return f"城市{city}天气为晴天，气温26摄氏度，空气湿度50%，南风1级，AQI21，最近6小时降雨概率极低"


@tool(description="获取用户所在城市名称")
def get_user_location() -> str:
    return random.choice(["深圳", "合肥", "杭州"])


@tool(description="获取当前登录账号的用户名，该用户名是CSV报告查询使用的用户标识")
def get_user_id(runtime: ToolRuntime) -> str:
    """从可信的运行上下文读取登录用户名，不再随机生成或自动编号。"""
    return str(runtime.context["user_id"])


@tool(description="获取当前月份")
def get_current_month() -> str:
    return random.choice(month_arr)


def _month_matches(record_month: str, requested_month: str) -> bool:
    """兼容 YYYY-MM、YYYY-M、YYYY年M月、M月和 M。"""
    record_month = record_month.strip()
    requested_month = requested_month.strip()

    if record_month == requested_month:
        return True

    year_month_match = re.fullmatch(
        r"(\d{4})(?:-|/|年)(\d{1,2})月?",
        requested_month,
    )
    if year_month_match:
        year, month = year_month_match.groups()
        return record_month == f"{year}-{int(month):02d}"

    month_match = re.fullmatch(r"(\d{1,2})月?", requested_month)
    if month_match:
        month = int(month_match.group(1))
        return 1 <= month <= 12 and record_month.endswith(f"-{month:02d}")

    return False


def has_user_records(user_id: str) -> bool:
    """判断 CSV 中是否存在该登录用户的任意使用记录。"""
    records_path = get_abs_path("data/external/records.csv")
    requested_user_id = str(user_id).strip()

    try:
        with open(records_path, "r", encoding="utf-8-sig", newline="") as file:
            return any(
                record.get("user_id", "").strip() == requested_user_id
                for record in csv.DictReader(file)
            )
    except (OSError, csv.Error, UnicodeError):
        return False


@tool(
    description="从CSV中获取当前登录用户在指定月份的使用记录；user_id应传入get_user_id的结果，系统会强制按登录身份校验"
)
def fetch_external_data(user_id: str, month: str, runtime: ToolRuntime) -> str:
    records_path = get_abs_path("data/external/records.csv")
    # 不信任模型传入的 ID，始终以登录会话中的用户身份为准。
    requested_user_id = str(runtime.context["user_id"]).strip()
    requested_month = str(month).strip()

    try:
        with open(records_path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for record in reader:
                if record.get("user_id", "").strip() != requested_user_id:
                    continue
                if not _month_matches(record.get("month", ""), requested_month):
                    continue

                cleaning_metrics = record.get("cleaning_metrics", "").replace("\\n", "\n")
                device_status = record.get("device_status", "").replace("\\n", "\n")

                return (
                    f"用户ID：{record.get('user_id', '')}\n"
                    f"月份：{record.get('month', '')}\n"
                    f"用户画像：{record.get('user_profile', '')}\n"
                    f"清扫指标：\n{cleaning_metrics}\n"
                    f"设备状态：\n{device_status}\n"
                    f"使用总结：{record.get('usage_summary', '')}"
                )
    except (OSError, csv.Error, UnicodeError):
        return "未找到该用户的相关使用报告"

    return "未找到该用户的相关使用报告"

@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("请通过 ReactAgent 调用 fetch_external_data，以便注入登录用户上下文。")
