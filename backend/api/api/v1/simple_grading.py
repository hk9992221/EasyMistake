from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["simple-grading"])

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "simple_grading_records.json"


class GradingRecordCreate(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=50)
    paper_name: str = Field(..., min_length=1, max_length=80)
    score: float = Field(..., ge=0, le=150)
    comment: str = Field(default="", max_length=200)


class GradingRecord(GradingRecordCreate):
    id: str
    created_at: str


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _load_records() -> List[GradingRecord]:
    _ensure_data_file()
    raw = DATA_FILE.read_text(encoding="utf-8")
    items = json.loads(raw)
    return [GradingRecord(**item) for item in items]


def _save_records(records: List[GradingRecord]) -> None:
    DATA_FILE.write_text(
        json.dumps([item.model_dump() for item in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@router.get("/grading", response_class=HTMLResponse)
async def grading_page() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>简易试卷批改入口</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --card: #ffffff;
      --line: #d8dee4;
      --brand: #0f766e;
      --brand-deep: #115e59;
      --text: #0f172a;
      --muted: #64748b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
      color: var(--text);
      background: linear-gradient(140deg, #f5f7fa 0%, #ecfdf5 100%);
      min-height: 100vh;
      padding: 20px 12px 32px;
    }
    .container {
      width: min(760px, 100%);
      margin: 0 auto;
      display: grid;
      gap: 12px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
    }
    h1 { font-size: 20px; margin: 0 0 6px; }
    .hint { color: var(--muted); margin: 0; font-size: 13px; }
    label {
      display: block;
      font-size: 13px;
      color: #334155;
      margin-bottom: 6px;
      margin-top: 10px;
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      font-size: 15px;
      outline: none;
      background: #fff;
    }
    textarea { min-height: 70px; resize: vertical; }
    input:focus, textarea:focus { border-color: var(--brand); }
    button {
      width: 100%;
      margin-top: 12px;
      border: none;
      border-radius: 10px;
      background: var(--brand);
      color: #fff;
      padding: 11px 14px;
      font-size: 15px;
      font-weight: 600;
    }
    button:active { background: var(--brand-deep); }
    .list { display: grid; gap: 8px; margin-top: 10px; }
    .item {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: #fcfffd;
    }
    .item-top {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 14px;
      align-items: center;
    }
    .score {
      color: var(--brand);
      font-weight: 700;
      white-space: nowrap;
    }
    .meta {
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      word-break: break-all;
    }
  </style>
</head>
<body>
  <div class="container">
    <section class="card">
      <h1>简易试卷批改入口</h1>
      <p class="hint">同一端口提供页面和接口，手机浏览器直接可用。</p>
      <form id="gradingForm">
        <label>学生姓名</label>
        <input id="studentName" placeholder="例如：张三" required />
        <label>试卷名称</label>
        <input id="paperName" placeholder="例如：七年级数学期中卷" required />
        <label>分数</label>
        <input id="score" type="number" min="0" max="150" step="0.5" placeholder="例如：96.5" required />
        <label>评语（可选）</label>
        <textarea id="comment" placeholder="例如：计算准确，压轴题再加强"></textarea>
        <button type="submit">提交批改记录</button>
      </form>
    </section>

    <section class="card">
      <h1 style="margin-bottom: 0;">最近批改记录</h1>
      <div id="recordList" class="list"></div>
    </section>
  </div>

  <script>
    const form = document.getElementById("gradingForm");
    const listEl = document.getElementById("recordList");

    function escapeHtml(text) {
      return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function renderRecords(records) {
      if (!records.length) {
        listEl.innerHTML = "<p class='hint'>还没有批改记录。</p>";
        return;
      }
      listEl.innerHTML = records.map((item) => `
        <article class="item">
          <div class="item-top">
            <strong>${escapeHtml(item.student_name)} - ${escapeHtml(item.paper_name)}</strong>
            <span class="score">${item.score} 分</span>
          </div>
          ${item.comment ? `<div>${escapeHtml(item.comment)}</div>` : ""}
          <div class="meta">${escapeHtml(item.created_at)}</div>
        </article>
      `).join("");
    }

    async function loadRecords() {
      const resp = await fetch("/api/v1/grading/records");
      const data = await resp.json();
      renderRecords(data.records || []);
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        student_name: document.getElementById("studentName").value.trim(),
        paper_name: document.getElementById("paperName").value.trim(),
        score: Number(document.getElementById("score").value),
        comment: document.getElementById("comment").value.trim(),
      };
      const resp = await fetch("/api/v1/grading/records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        alert("提交失败，请检查输入内容。");
        return;
      }
      form.reset();
      await loadRecords();
    });

    loadRecords();
  </script>
</body>
</html>
"""


@router.get("/grading/records")
async def list_grading_records():
    records = _load_records()
    records.sort(key=lambda x: x.created_at, reverse=True)
    return {"records": [item.model_dump() for item in records[:100]]}


@router.post("/grading/records")
async def create_grading_record(payload: GradingRecordCreate):
    records = _load_records()
    item = GradingRecord(
        id=uuid4().hex,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **payload.model_dump(),
    )
    records.append(item)
    _save_records(records)
    return {"record": item.model_dump()}
