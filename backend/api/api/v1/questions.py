from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from api.core.database import get_db
from api.core.deps import get_current_user
from api.services.question_service import question_service
from api.services.answer_service import answer_service
from api.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionListParams,
    QuestionImageItem,
)
from api.schemas.answer import AnswerResponse, AnswerUpdate, AnswerImageItem
from api.schemas.common import PaginatedResponse
from api.models.user import User, UserRole
from api.models.answer import Answer
from api.models.answer_image import AnswerImage
from api.models.question_image import QuestionImage
from api.models.image import Image
from api.models.question import Question
from api.core.exceptions import ForbiddenError, NotFoundError


router = APIRouter(prefix="/questions", tags=["Questions"])


def _build_image_proxy_url(request: Request | None, image_id: UUID) -> str:
    relative_path = f"/api/v1/images/{image_id}/file"
    if request is None:
        return relative_path
    url = f"{str(request.base_url).rstrip('/')}{relative_path}"
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            return f"{url}?token={token}"
    return url


async def _serialize_question_with_images(
    db: AsyncSession,
    question: Question,
    request: Request = None
) -> dict:
    """序列化题目，包含题干图片信息"""
    result = {
        "id": str(question.id),
        "user_id": str(question.user_id),
        "paper_id": str(question.paper_id) if question.paper_id else None,
        "subject": question.subject,
        "book_name": question.book_name,
        "chapter_name": question.chapter_name,
        "page_no": question.page_no,
        "question_no": question.question_no,
        "source_anchor": question.source_anchor,
        "type": question.type,
        "difficulty": question.difficulty,
        "stem_text": question.stem_text,
        "stem_latex": question.stem_latex,
        "appendix": question.appendix,
        "content_json": question.content_json,
        "paper_meta": question.paper_meta,
        "tags_json": question.tags_json,
        "knowledge_points_json": question.knowledge_points_json,
        "from_extraction_id": str(question.from_extraction_id) if question.from_extraction_id else None,
        "is_deleted": question.is_deleted,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "stem_images": []
    }

    # 查询关联的题干图片
    stmt = (
        select(QuestionImage, Image)
        .join(Image, QuestionImage.image_id == Image.id)
        .where(QuestionImage.question_id == question.id)
        .order_by(QuestionImage.order_index)
    )
    images_result = await db.execute(stmt)
    images = images_result.all()

    for question_image, image in images:
        result["stem_images"].append(
            QuestionImageItem(
                image_id=image.id,
                order_index=question_image.order_index,
                url=_build_image_proxy_url(request, image.id)
            ).model_dump()
        )

    return result


async def _serialize_answer_with_images(db: AsyncSession, answer: Answer, request: Request = None) -> dict:
    """序列化答案，包含图片信息"""
    result = {
        "question_id": str(answer.question_id),
        "answer_type": answer.answer_type,
        "answer_text": answer.answer_text,
        "answer_latex": answer.answer_latex,
        "explanation_text": answer.explanation_text,
        "explanation_latex": answer.explanation_latex,
        "content_json": answer.content_json,
        "from_extraction_id": str(answer.from_extraction_id) if answer.from_extraction_id else None,
        "from_api_call_id": str(answer.from_api_call_id) if answer.from_api_call_id else None,
        "updated_by": str(answer.updated_by) if answer.updated_by else None,
        "created_at": answer.created_at,
        "updated_at": answer.updated_at,
        "images": []
    }

    # 查询关联的图片
    stmt = (
        select(AnswerImage, Image)
        .join(Image, AnswerImage.image_id == Image.id)
        .where(AnswerImage.question_id == answer.question_id)
        .order_by(AnswerImage.order_index)
    )
    images_result = await db.execute(stmt)
    images = images_result.all()

    for answer_image, image in images:
        # Use direct MinIO URL (bucket is public)
        result["images"].append(
            AnswerImageItem(
                image_id=image.id,
                order_index=answer_image.order_index,
                url=_build_image_proxy_url(request, image.id)
            ).model_dump()
        )

    return result


@router.get("/user/common-tags", response_model=dict)
async def get_user_common_tags(
    limit: int = Query(4, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户最常用的tag"""
    tags = await question_service.get_user_common_tags(db, current_user.id, limit)
    return {"tags": tags}


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    question = await question_service.create_question(db, current_user.id, question_data)
    return await _serialize_question_with_images(db, question, request)


@router.get("", response_model=PaginatedResponse[QuestionResponse], include_in_schema=False)
@router.get("/", response_model=PaginatedResponse[QuestionResponse])
async def list_questions(
    subject: Optional[str] = None,
    book_name: Optional[str] = None,
    chapter_name: Optional[str] = None,
    paper_id: Optional[UUID] = None,
    page_no: Optional[int] = None,
    question_no: Optional[str] = None,
    type: Optional[str] = None,
    difficulty: Optional[str] = None,
    tags_json: Optional[list[str]] = Query(None),
    knowledge_point_q: Optional[str] = None,
    q: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    params = QuestionListParams(
        subject=subject,
        book_name=book_name,
        chapter_name=chapter_name,
        paper_id=paper_id,
        page_no=page_no,
        question_no=question_no,
        type=type,
        difficulty=difficulty,
        tags_json=tags_json,
        knowledge_point_q=knowledge_point_q,
        q=q,
        start_date=start_date,
        end_date=end_date,
    )

    is_admin = current_user.role == UserRole.ADMIN
    skip = (page - 1) * page_size

    questions, total = await question_service.list_questions(
        db,
        current_user.id,
        params,
        is_admin=is_admin,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # 序列化题目，包含图片信息
    items_with_images = []
    for question in questions:
        items_with_images.append(await _serialize_question_with_images(db, question, request))

    return PaginatedResponse(
        items=items_with_images,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    question = await question_service.get_question_by_id(db, question_id)
    if question is None:
        raise NotFoundError(detail="Question not found")

    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and question.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this question")

    return await _serialize_question_with_images(db, question, request)


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    question_data: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    is_admin = current_user.role == UserRole.ADMIN
    question = await question_service.update_question(
        db,
        question_id,
        question_data,
        current_user.id,
        is_admin=is_admin,
    )
    return await _serialize_question_with_images(db, question, request)


@router.delete("/{question_id}")
async def delete_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    await question_service.delete_question(
        db,
        question_id,
        current_user.id,
        is_admin=is_admin,
    )
    return {"message": "Question deleted successfully"}


@router.get("/{question_id}/answer", response_model=AnswerResponse)
async def get_answer(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    question = await question_service.get_question_by_id(db, question_id)
    if question is None:
        raise NotFoundError(detail="Question not found")

    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and question.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this answer")

    answer = await answer_service.get_answer_by_question_id(db, question_id)
    if not answer:
        raise NotFoundError(detail="Answer not found")

    # 手动序列化答案，包含图片信息
    return await _serialize_answer_with_images(db, answer, request)


@router.put("/{question_id}/answer", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
async def upsert_answer(
    question_id: UUID,
    answer_data: AnswerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    question = await question_service.get_question_by_id(db, question_id)
    if question is None:
        raise NotFoundError(detail="Question not found")

    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and question.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to update this answer")

    answer = await answer_service.upsert_answer(
        db,
        question_id,
        answer_data,
        updater_id=current_user.id,
    )

    # 手动序列化答案，包含图片信息
    return await _serialize_answer_with_images(db, answer, request)


@router.post("/{question_id}/images", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_question_image(
    question_id: UUID,
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为题目添加图片"""
    question = await question_service.get_question_by_id(db, question_id)
    if question is None:
        raise NotFoundError(detail="Question not found")

    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and question.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to modify this question")

    # 获取当前最大的 order_index
    stmt = select(func.max(QuestionImage.order_index)).where(
        QuestionImage.question_id == question_id
    )
    result = await db.execute(stmt)
    max_order = result.scalar() or 0

    # 创建关联
    question_image = QuestionImage(
        question_id=question_id,
        image_id=image_id,
        order_index=max_order + 1
    )
    db.add(question_image)
    await db.commit()

    return {"message": "Image added to question successfully"}


@router.delete("/{question_id}/images/{image_id}")
async def remove_question_image(
    question_id: UUID,
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从题干移除图片"""
    question = await question_service.get_question_by_id(db, question_id)
    if question is None:
        raise NotFoundError(detail="Question not found")

    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and question.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to modify this question")

    # 删除关联
    stmt = select(QuestionImage).where(
        QuestionImage.question_id == question_id,
        QuestionImage.image_id == image_id
    )
    result = await db.execute(stmt)
    question_image = result.scalar_one_or_none()

    if question_image:
        await db.delete(question_image)
        await db.commit()

    return {"message": "Image removed from question successfully"}


@router.patch("/{question_id}/images/reorder")
async def reorder_question_images(
    question_id: UUID,
    image_ids: list[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重新排列题干图片顺序"""
    question = await question_service.get_question_by_id(db, question_id)
    if question is None:
        raise NotFoundError(detail="Question not found")

    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and question.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to modify this question")

    # 更新所有图片的 order_index
    for index, image_id in enumerate(image_ids):
        stmt = select(QuestionImage).where(
            QuestionImage.question_id == question_id,
            QuestionImage.image_id == image_id
        )
        result = await db.execute(stmt)
        question_image = result.scalar_one_or_none()
        if question_image:
            question_image.order_index = index + 1

    await db.commit()

    return {"message": "Images reordered successfully"}
