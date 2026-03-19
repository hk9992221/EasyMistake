import asyncio
import json
import re
from uuid import UUID
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.models.extraction import QuestionExtraction, ExtractionStatus
from api.models.extraction_image import ExtractionImage
from api.models.image import Image
from api.models.api_call_log import ApiCallLog
from api.schemas.extraction import ExtractionCreate, DraftQuestion, DraftQuestionsResponse
from api.core.exceptions import NotFoundError, ForbiddenError
from api.core.jobs import create_job
from api.models.job import JobType
from api.services.image_service import image_service
from api.services.ocr_service import ocr_service
from api.services.pricing_service import pricing_service


class ExtractionService:
    """Service for extraction operations"""

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """Strip markdown code fence if OCR wraps JSON in ```json ... ```."""
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)
        return stripped.strip()

    @staticmethod
    def _normalize_choices(choices: Any) -> Optional[str]:
        """
        Normalize choices to 'A. ...\\nB. ...' text.
        Supports:
        - already-joined string
        - list[str]
        - list[{"label":"A","text":"..."}]
        - dict[label->text]
        """
        if choices is None:
            return None

        if isinstance(choices, str):
            return choices.strip() or None

        if isinstance(choices, dict):
            lines = [f"{k}. {v}" for k, v in choices.items() if v is not None]
            return "\n".join(lines).strip() or None

        if isinstance(choices, list):
            lines: List[str] = []
            for idx, item in enumerate(choices):
                if isinstance(item, str):
                    if item.strip():
                        lines.append(item.strip())
                    continue
                if isinstance(item, dict):
                    label = str(item.get("label") or item.get("key") or chr(ord("A") + idx)).strip()
                    text = str(item.get("text") or item.get("content") or "").strip()
                    if text:
                        lines.append(f"{label}. {text}")
            return "\n".join([line for line in lines if line]).strip() or None

        return None

    def _extract_question_from_dict(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract one question from normalized dict payload.
        Handles both direct and nested `content`.
        """
        nested = payload.get("content")
        if isinstance(nested, dict):
            return self._extract_question_from_dict(nested)

        if isinstance(nested, str):
            try:
                parsed = json.loads(self._strip_code_fence(nested))
                if isinstance(parsed, dict):
                    parsed_question = self._extract_question_from_dict(parsed)
                    if parsed_question:
                        return parsed_question
            except Exception:
                pass

        problem = payload.get("problem") or payload.get("question") or payload.get("stem") or payload.get("stem_text")
        choices = self._normalize_choices(payload.get("choices") or payload.get("options"))
        number = payload.get("number") or payload.get("question_no") or payload.get("index") or ""
        appendix = payload.get("appendix")

        if problem is None and choices is None:
            return None

        return {
            "number": str(number or ""),
            "problem": str(problem or ""),
            "choices": choices,
            "appendix": appendix,
        }

    def _normalize_ocr_questions(self, ocr_result: Any) -> List[Dict[str, Any]]:
        """Normalize OCR result to unified question dict list."""
        normalized: List[Dict[str, Any]] = []

        def append_if_valid(item: Optional[Dict[str, Any]]) -> None:
            if item and (item.get("problem") or item.get("choices")):
                normalized.append(item)

        if isinstance(ocr_result, dict):
            raw_list = ocr_result.get("questions")
            if isinstance(raw_list, list):
                for raw in raw_list:
                    if isinstance(raw, dict):
                        append_if_valid(self._extract_question_from_dict(raw))
            else:
                append_if_valid(self._extract_question_from_dict(ocr_result))
        elif isinstance(ocr_result, list):
            for raw in ocr_result:
                if isinstance(raw, dict):
                    append_if_valid(self._extract_question_from_dict(raw))

        return normalized

    async def create_extraction(
        self,
        db: AsyncSession,
        user_id: UUID,
        extraction_data: ExtractionCreate,
        is_admin: bool = False,
    ) -> QuestionExtraction:
        result = await db.execute(select(Image).where(Image.id.in_(extraction_data.image_ids)))
        images = result.scalars().all()

        if len(images) != len(extraction_data.image_ids):
            raise NotFoundError(detail="One or more images not found")

        if not is_admin:
            for image in images:
                if image.user_id != user_id:
                    raise ForbiddenError(detail="You don't have access to one or more images")

        extraction = QuestionExtraction(
            user_id=user_id,
            paper_id=extraction_data.paper_id,
            status=ExtractionStatus.PENDING.value,
            model_name=extraction_data.model_name,
            params=extraction_data.params,
        )

        db.add(extraction)
        await db.commit()
        await db.refresh(extraction)

        for order_index, image_id in enumerate(extraction_data.image_ids):
            db.add(
                ExtractionImage(
                    extraction_id=extraction.id,
                    image_id=image_id,
                    order_index=order_index,
                )
            )

        await db.commit()

        await create_job(
            db,
            user_id=user_id,
            job_type=JobType.EXTRACTION,
            payload={"extraction_id": str(extraction.id)},
        )

        return extraction

    async def get_extraction(self, db: AsyncSession, extraction_id: UUID) -> QuestionExtraction:
        result = await db.execute(select(QuestionExtraction).where(QuestionExtraction.id == extraction_id))
        return result.scalar_one_or_none()

    async def list_extractions(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[QuestionExtraction]:
        query = select(QuestionExtraction).order_by(QuestionExtraction.created_at.desc())
        if not is_admin:
            query = query.where(QuestionExtraction.user_id == user_id)

        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_draft_questions(self, extraction: QuestionExtraction) -> DraftQuestionsResponse:
        draft_questions = []
        raw_questions = []
        if extraction.raw_json and isinstance(extraction.raw_json, dict):
            raw_questions = extraction.raw_json.get("questions", [])

        for raw in raw_questions:
            if not isinstance(raw, dict):
                continue
            parsed = self._extract_question_from_dict(raw) or raw
            draft_questions.append(
                DraftQuestion(
                    number=str(parsed.get("number", "")),
                    problem=str(parsed.get("problem", "")),
                    choices=self._normalize_choices(parsed.get("choices")),
                    appendix=parsed.get("appendix"),
                )
            )

        return DraftQuestionsResponse(extraction_id=extraction.id, questions=draft_questions)

    async def run_extraction(self, db: AsyncSession, extraction: QuestionExtraction) -> QuestionExtraction:
        extraction.status = ExtractionStatus.RUNNING.value
        extraction.error = None
        await db.commit()
        await db.refresh(extraction)

        result = await db.execute(
            select(Image)
            .join(ExtractionImage, ExtractionImage.image_id == Image.id)
            .where(ExtractionImage.extraction_id == extraction.id)
            .order_by(ExtractionImage.order_index.asc())
        )
        images = list(result.scalars().all())
        if not images:
            extraction.status = ExtractionStatus.FAILED.value
            extraction.error = "No images attached to extraction"
            await db.commit()
            await db.refresh(extraction)
            raise NotFoundError(detail="No images attached to extraction")

        questions = []
        model_name = extraction.model_name or "qwen3-vl-flash"
        try:
            for image in images:
                image_bytes = await asyncio.to_thread(image_service.fetch_image_bytes, image.object_key)
                ocr_result = await ocr_service.recognize(image_bytes, image.mime, model_name)

                api_info = ocr_result.pop("_api_info", None) if isinstance(ocr_result, dict) else None
                if api_info:
                    usage = api_info.get("usage", {})
                    cost_usd = pricing_service.calculate_cost_from_usage(
                        model_name, usage, target_currency="CNY"
                    )

                    api_log = ApiCallLog(
                        user_id=extraction.user_id,
                        purpose="extraction",
                        provider=api_info.get("provider"),
                        model_name=api_info.get("model_name"),
                        request_json=api_info.get("request", {}),
                        response_json=api_info.get("response", {}),
                        usage_json=usage or {},
                        cost_usd=cost_usd,
                        status_code=api_info.get("status_code"),
                        latency_ms=api_info.get("latency_ms"),
                    )
                    db.add(api_log)

                normalized_questions = self._normalize_ocr_questions(ocr_result)
                if normalized_questions:
                    questions.extend(normalized_questions)
                else:
                    # Backward-compatible fallback for unexpected payloads
                    if isinstance(ocr_result, dict):
                        if isinstance(ocr_result.get("questions"), list):
                            questions.extend(ocr_result["questions"])
                        else:
                            questions.append(ocr_result)
                    elif isinstance(ocr_result, list):
                        questions.extend(ocr_result)

        except Exception as exc:
            extraction.status = ExtractionStatus.FAILED.value
            extraction.error = str(exc)
            await db.commit()
            await db.refresh(extraction)
            raise

        extraction.status = ExtractionStatus.DONE.value
        extraction.raw_json = {"questions": questions}
        await db.commit()
        await db.refresh(extraction)
        return extraction


extraction_service = ExtractionService()
