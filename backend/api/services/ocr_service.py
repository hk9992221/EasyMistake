import asyncio
import base64
import json
import time
from typing import Any, Dict

from openai import OpenAI

from api.core.config import settings


SYSTEM_PROMPT = """\
你是"题目结构化提取器"。任务：从用户输入中提取题目信息并输出严格 JSON（只能输出 JSON，不能输出其它文字），同时尽量全用$...$或$$...$$的公式化表达，减少直接打η、τ这种非unicode字符。

【输出 JSON Schema】
- number: string，必填。题号/例题编号，如 "3.12"、"例1.1"；缺失则输出 "UNKNOWN"。
- problem: string，必填。完整题干文本，不包含选项；数学公式使用 LaTeX（建议 $...$ 或 $$...$$）。
- choices: string，可选。仅当为选择题时输出，格式："A. 选项内容\\nB. 选项内容\\nC. 选项内容\\nD. 选项内容"；非选择题不输出该字段。
- appendix: string，可选。题目附录/补充材料，如表格、图表说明等；如果没有则不输出该字段。

【规则】
1) 只输出一个 JSON 对象，不要 Markdown、不要代码块、不要解释。
2) problem字段只包含题干本身，绝对不能包含A/B/C/D选项。
3) choices字段必须按格式输出，每行一个选项：A. xxx\\nB. xxx\\nC. xxx\\nD. xxx。
4) 保留题干原意与顺序，包含(1)(2)等小问；换行使用 \\n。
5) 如果选项中包含"以上都对"等，也要作为单独选项列出。
6) 附录材料单独放在appendix字段，不要混入problem或choices。

【参考示例 - 选择题】
{"number":"3.12","problem":"求下列方程的解：$$x^2+6x+9=0$$","choices":"A. $x=-3$\\nB. $x=3$\\nC. $x=-6$\\nD. $x=6$"}

【参考示例 - 带附录的选择题】
{"number":"5.1","problem":"设$u(n)=\\sqrt{\\arctan(n+k)-\\arctan(n)}$，$k$为正常数，则( )$$\\sum_{n=1}^{\\infty}(-1)^nu_n$$","choices":"A.绝对收敛\\nB.条件收敛\\nC.发散\\nD.敛散性与$k$有关"}

【参考示例 - 非选择题】
{"number":"3.15","problem":"求以下联合密度的 $(X,Y)$ 的边缘密度 $f_X(x)$ 和 $f_Y(y)$：\\n(1) $f_1(x,y)=\\begin{cases} e^{-y}, & 0<x<y, \\\\ 0, & \\text{其他}. \\end{cases}$\\n(2) $f_2(x,y)=\\begin{cases} \\dfrac{5}{4}(x^2+y), & 0<y<1-x^2, \\\\ 0, & \\text{其他}. \\end{cases}$"}
"""


class OCRService:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    def _recognize_sync(self, image_bytes: bytes, mime: str, model_name: str) -> Dict[str, Any]:
        started = time.perf_counter()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        request_payload = {
            "model": model_name,
            "response_format": {"type": "json_object"},
            "mime": mime,
            "image_bytes": len(image_bytes),
        }

        try:
            completion = self._client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{base64_image}"},
                            }
                        ],
                    },
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "error": str(exc),
                "_api_info": {
                    "provider": "dashscope_compatible",
                    "model_name": model_name,
                    "request": request_payload,
                    "response": {"error": str(exc)},
                    "usage": {},
                    "status_code": None,
                    "latency_ms": latency_ms,
                },
            }

        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = {
            "prompt_tokens": getattr(completion.usage, "prompt_tokens", 0) if completion.usage else 0,
            "completion_tokens": getattr(completion.usage, "completion_tokens", 0) if completion.usage else 0,
            "total_tokens": getattr(completion.usage, "total_tokens", 0) if completion.usage else 0,
        }

        content = completion.choices[0].message.content if completion.choices else None
        if not content:
            return {
                "error": "Empty OCR response",
                "_api_info": {
                    "provider": "dashscope_compatible",
                    "model_name": model_name,
                    "request": request_payload,
                    "response": {"content": None},
                    "usage": usage,
                    "status_code": 200,
                    "latency_ms": latency_ms,
                },
            }

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"raw": content}

        if not isinstance(parsed, dict):
            parsed = {"content": parsed}

        parsed["_api_info"] = {
            "provider": "dashscope_compatible",
            "model_name": getattr(completion, "model", model_name),
            "request": request_payload,
            "response": {"content": content},
            "usage": usage,
            "status_code": 200,
            "latency_ms": latency_ms,
        }
        return parsed

    async def recognize(self, image_bytes: bytes, mime: str, model_name: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._recognize_sync, image_bytes, mime, model_name)


ocr_service = OCRService()
