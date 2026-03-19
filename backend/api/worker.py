#!/usr/bin/env python
"""Background worker for processing async export jobs."""

import asyncio
import hashlib
import logging
import re
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import quote
from uuid import UUID

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.core.config import settings
from api.core.database import get_db
from api.core.datetime_utils import utcnow
from api.core.jobs import complete_job, fetch_next_job
from api.core.s3 import s3_client
from api.models.export import Export, ExportFormat, ExportStatus
from api.models.export_item import ExportItem
from api.models.image import Image
from api.models.job import Job, JobType
from api.models.paper_set import PaperSet
from api.services.export_service import export_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class ExportWorker:
    """Worker for processing export jobs."""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.temp_dir = Path(settings.export_output_dir) / 'temp'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._last_cleanup_at: datetime | None = None

    async def process_job(self, db: AsyncSession, job: Job) -> None:
        logger.info('Processing job %s of type %s', job.id, job.type)
        try:
            if job.type == JobType.EXPORT.value:
                await self._process_export_job(db, job)
            else:
                await complete_job(db, job.id, success=False, error=f'Unknown job type: {job.type}')
        except Exception as exc:
            logger.exception('Error processing job %s: %s', job.id, exc)
            await complete_job(db, job.id, success=False, error=str(exc))

    async def maintenance_tick(self, db: AsyncSession) -> None:
        interval = max(settings.EXPORT_CLEANUP_INTERVAL_SECONDS, 0)
        if interval == 0:
            return

        now = utcnow()
        if self._last_cleanup_at and (now - self._last_cleanup_at).total_seconds() < interval:
            return

        self._last_cleanup_at = now
        await self._cleanup_expired_exports(db)

    async def _cleanup_expired_exports(self, db: AsyncSession) -> None:
        cutoff = utcnow() - timedelta(days=settings.EXPORT_RETENTION_DAYS)
        result = await db.execute(
            select(Export)
            .where(
                func.coalesce(Export.finished_at, Export.created_at) < cutoff,
                Export.status.in_([ExportStatus.DONE.value, ExportStatus.FAILED.value]),
            )
            .order_by(func.coalesce(Export.finished_at, Export.created_at))
            .limit(200)
        )
        exports = list(result.scalars().all())
        if not exports:
            return

        deleted_count = 0
        skipped_count = 0
        for export in exports:
            if export.object_key:
                deleted = s3_client.delete_file(export.object_key)
                if not deleted:
                    skipped_count += 1
                    logger.warning(
                        "Skip deleting export record %s because S3 deletion failed: %s",
                        export.id,
                        export.object_key,
                    )
                    continue

            await db.delete(export)
            deleted_count += 1

        if deleted_count > 0:
            await db.commit()
            logger.info(
                "Export cleanup completed: deleted=%s skipped=%s cutoff=%s",
                deleted_count,
                skipped_count,
                cutoff.isoformat(),
            )

    async def _process_export_job(self, db: AsyncSession, job: Job) -> None:
        export_id = UUID(job.payload['export_id'])
        format_type = job.payload['format']

        result = await db.execute(select(Export).where(Export.id == export_id))
        export = result.scalar_one_or_none()
        if not export:
            raise ValueError(f'Export {export_id} not found')

        if export.status != ExportStatus.PENDING.value:
            logger.warning('Export %s is not pending, skipping', export_id)
            return

        export.status = ExportStatus.RUNNING.value
        await db.commit()

        export_temp_dir = self.temp_dir / str(export_id)
        export_temp_dir.mkdir(exist_ok=True)

        try:
            if export.paper_set_id is None:
                raise ValueError(f'Export {export_id} has no paper_set_id')

            await export_service.build_export_items(db, export_id, export.paper_set_id)
            file_path, size_bytes, sha256_hash = await self._generate_export(db, export_id, format_type, export_temp_dir)

            s3_key = f'exports/{export_id}/{file_path.name}'
            uploaded = s3_client.upload_file(file_path, s3_key, content_type='application/zip')
            if not uploaded:
                raise RuntimeError('Failed to upload export file to S3')

            file_path.unlink(missing_ok=True)
            shutil.rmtree(export_temp_dir, ignore_errors=True)

            export.status = ExportStatus.DONE.value
            export.object_key = s3_key
            export.size_bytes = size_bytes
            export.sha256 = sha256_hash
            export.finished_at = utcnow()
            await db.commit()

            await complete_job(db, job.id, success=True)
        except Exception:
            shutil.rmtree(export_temp_dir, ignore_errors=True)
            export.status = ExportStatus.FAILED.value
            export.error = 'Export failed'
            export.finished_at = utcnow()
            await db.commit()
            raise

    async def _generate_export(
        self,
        db: AsyncSession,
        export_id: UUID,
        format_type: str,
        temp_dir: Path,
    ) -> tuple[Path, int, str]:
        item_result = await db.execute(
            select(ExportItem).where(ExportItem.export_id == export_id).order_by(ExportItem.order_index)
        )
        items = list(item_result.scalars().all())

        export_result = await db.execute(
            select(Export, PaperSet)
            .join(PaperSet, Export.paper_set_id == PaperSet.id)
            .where(Export.id == export_id)
        )
        row = export_result.first()
        if not row:
            raise ValueError(f'Export {export_id} or associated paper set not found')
        export, paper_set = row

        image_ids = self._collect_image_ids(items)
        images_map = await self._fetch_images(db, image_ids)

        resources_dir = temp_dir / 'resources'
        resources_dir.mkdir(exist_ok=True)
        downloaded_images = await self._download_images(images_map, resources_dir)

        review_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/dashboard/paper-sets/{paper_set.id}/review"
        review_qr_filename = await self._download_review_qr_image(review_url, resources_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = ''.join(c for c in paper_set.title if c.isalnum() or c in (' ', '-', '_')).strip() or 'paper'
        filename = f'{export.user_id}_{safe_title}_{timestamp}'

        if format_type == ExportFormat.MARKDOWN_ZIP.value:
            return await self._generate_markdown_zip(filename, items, paper_set, temp_dir, downloaded_images, review_url, review_qr_filename)
        if format_type == ExportFormat.LATEX_ZIP.value:
            return await self._generate_latex_zip(filename, items, paper_set, temp_dir, downloaded_images, review_url, review_qr_filename)

        raise ValueError(f'Unsupported format: {format_type}')

    def _collect_image_ids(self, items: List[ExportItem]) -> Set[str]:
        image_ids: Set[str] = set()
        for item in items:
            snapshot = item.snapshot_json or {}

            stem_images = snapshot.get('stem_images', [])
            if isinstance(stem_images, list):
                for img in stem_images:
                    if isinstance(img, dict) and img.get('image_id'):
                        image_ids.add(str(img['image_id']))

            content = snapshot.get('content_json', {})
            if isinstance(content, dict):
                for img_id in content.get('stem_images', []) or []:
                    image_ids.add(str(img_id))
                option_images = content.get('option_images', {})
                if isinstance(option_images, dict):
                    for ids in option_images.values():
                        if isinstance(ids, list):
                            for img_id in ids:
                                image_ids.add(str(img_id))
                for img_id in content.get('answer_images', []) or []:
                    image_ids.add(str(img_id))

        return image_ids

    async def _fetch_images(self, db: AsyncSession, image_ids: Set[str]) -> Dict[str, Image]:
        if not image_ids:
            return {}
        uuids = []
        for image_id in image_ids:
            try:
                uuids.append(UUID(image_id))
            except ValueError:
                continue
        if not uuids:
            return {}
        result = await db.execute(select(Image).where(Image.id.in_(uuids)))
        images = result.scalars().all()
        return {str(img.id): img for img in images}

    async def _download_images(self, images_map: Dict[str, Image], resources_dir: Path) -> Dict[str, str]:
        downloaded: Dict[str, str] = {}
        for image_id, image in images_map.items():
            if not image.object_key:
                continue
            ext = Path(image.object_key).suffix or '.jpg'
            local_filename = f'{image_id}{ext}'
            local_path = resources_dir / local_filename
            if s3_client.download_file(image.object_key, local_path):
                downloaded[image_id] = local_filename
        return downloaded

    async def _download_review_qr_image(self, review_url: str, resources_dir: Path) -> str:
        qr_filename = 'review_qr.png'
        qr_path = resources_dir / qr_filename
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={quote(review_url, safe='')}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(qr_api)
                response.raise_for_status()
                qr_path.write_bytes(response.content)
                return qr_filename
        except Exception as exc:
            logger.warning('Failed to generate QR image: %s', exc)
            return ''

    async def _generate_markdown_zip(
        self,
        filename: str,
        items: List[ExportItem],
        paper_set: PaperSet,
        temp_dir: Path,
        downloaded_images: Dict[str, str],
        review_url: str,
        review_qr_filename: str,
    ) -> tuple[Path, int, str]:
        zip_path = temp_dir / f'{filename}.md.zip'
        paper_content = self._generate_complete_markdown_paper(
            paper_set, items, downloaded_images, review_url, review_qr_filename
        )

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('paper.md', paper_content)
            resources_dir = temp_dir / 'resources'
            if resources_dir.exists():
                for image_file in resources_dir.iterdir():
                    if image_file.is_file():
                        zipf.write(image_file, f'resources/{image_file.name}')

        return zip_path, zip_path.stat().st_size, self._calculate_sha256(zip_path)

    async def _generate_latex_zip(
        self,
        filename: str,
        items: List[ExportItem],
        paper_set: PaperSet,
        temp_dir: Path,
        downloaded_images: Dict[str, str],
        review_url: str,
        review_qr_filename: str,
    ) -> tuple[Path, int, str]:
        zip_path = temp_dir / f'{filename}.tex.zip'
        paper_content = self._generate_complete_latex_paper(
            paper_set, items, downloaded_images, review_url, review_qr_filename
        )

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('paper.tex', paper_content)
            resources_dir = temp_dir / 'resources'
            if resources_dir.exists():
                for image_file in resources_dir.iterdir():
                    if image_file.is_file():
                        zipf.write(image_file, f'resources/{image_file.name}')

        return zip_path, zip_path.stat().st_size, self._calculate_sha256(zip_path)

    def _generate_complete_markdown_paper(
        self,
        paper_set: PaperSet,
        items: List[ExportItem],
        downloaded_images: Dict[str, str],
        review_url: str,
        review_qr_filename: str,
    ) -> str:
        lines = [
            f'# {paper_set.title}',
            '',
        ]

        if paper_set.description:
            lines.extend([paper_set.description, ''])

        total_score = sum((item.snapshot_json or {}).get('score') or 0 for item in items)

        lines.extend([
            f'**学科**: {paper_set.subject or "N/A"}',
            f'**导出时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'**题目数量**: {len(items)}',
            f'**总分**: {total_score}',
            '',
            '## 批改入口二维码',
            '',
        ])

        if review_qr_filename:
            lines.extend([f'![批改页二维码](resources/{review_qr_filename})', ''])

        lines.extend([f'批改页链接: {review_url}', '', '---', ''])

        for idx, item in enumerate(items, 1):
            lines.extend(self._generate_markdown_question(item, idx, downloaded_images))
            lines.extend(['', '---', ''])

        return '\n'.join(lines)

    def _generate_markdown_question(
        self,
        item: ExportItem,
        question_num: int,
        downloaded_images: Dict[str, str],
    ) -> List[str]:
        snapshot = item.snapshot_json or {}
        content = snapshot.get('content_json', {}) if isinstance(snapshot.get('content_json', {}), dict) else {}

        lines = [
            f'## 第 {question_num} 题',
            '',
            f'**类型**: {snapshot.get("type", "N/A")}',
            f'**难度**: {snapshot.get("difficulty", "N/A")}',
        ]

        if snapshot.get('score') is not None:
            lines.append(f'**分值**: {snapshot.get("score")}')

        lines.append('')

        if snapshot.get('stem_text'):
            lines.append(str(snapshot.get('stem_text')))
            lines.append('')

        if snapshot.get('appendix'):
            lines.extend(['**附录**:', str(snapshot.get('appendix')), ''])

        stem_images = snapshot.get('stem_images', [])
        if isinstance(stem_images, list):
            for img in stem_images:
                if isinstance(img, dict):
                    img_id = str(img.get('image_id') or '')
                    if img_id in downloaded_images:
                        lines.extend([f'![题干图片](resources/{downloaded_images[img_id]})', ''])

        legacy_stem_images = content.get('stem_images', [])
        if isinstance(legacy_stem_images, list):
            for img_id in legacy_stem_images:
                img_id = str(img_id)
                if img_id in downloaded_images:
                    lines.extend([f'![题干图片](resources/{downloaded_images[img_id]})', ''])

        qtype = str(snapshot.get('type', '')).upper()
        if qtype in {'MCQ', 'SINGLE_CHOICE', 'MULTIPLE_CHOICE'}:
            options = self._extract_choice_options(content)
            if options:
                lines.extend(['### 选项', ''])
                for key, text in options:
                    lines.append(f'**{key}**. {text}')
                lines.append('')

        return lines

    def _generate_complete_latex_paper(
        self,
        paper_set: PaperSet,
        items: List[ExportItem],
        downloaded_images: Dict[str, str],
        review_url: str,
        review_qr_filename: str,
    ) -> str:
        total_score = sum((item.snapshot_json or {}).get('score') or 0 for item in items)

        lines = [
            '\\documentclass{article}',
            '\\usepackage[utf8]{inputenc}',
            '\\usepackage{amsmath}',
            '\\usepackage{amssymb}',
            '\\usepackage{geometry}',
            '\\usepackage{graphicx}',
            '\\usepackage{hyperref}',
            '\\geometry{a4paper, margin=1in}',
            '\\graphicspath{{./resources/}}',
            '',
            '\\title{' + paper_set.title + '}',
            f'\\author{{总分: {total_score} 分}}',
            '\\date{\\today}',
            '',
            '\\begin{document}',
            '',
            '\\maketitle',
            '',
        ]

        if paper_set.description:
            lines.extend([paper_set.description, ''])

        lines.extend([
            f'学科: {paper_set.subject or "N/A"}',
            f'题目数量: {len(items)}',
            '',
            '\\section*{批改入口二维码}',
            '',
        ])

        if review_qr_filename:
            lines.extend([f'\\includegraphics[width=0.25\\textwidth]{{{review_qr_filename}}}', ''])

        lines.extend([f'\\url{{{review_url}}}', '', '\\section*{试题}', ''])

        for item in items:
            lines.extend(self._generate_latex_question(item, downloaded_images))
            lines.append('')

        lines.append('\\end{document}')
        return '\n'.join(lines)

    def _generate_latex_question(self, item: ExportItem, downloaded_images: Dict[str, str]) -> List[str]:
        snapshot = item.snapshot_json or {}
        content = snapshot.get('content_json', {}) if isinstance(snapshot.get('content_json', {}), dict) else {}
        lines = [
            f'\\subsection*{{第 {item.order_index + 1} 题}}',
            '',
            f'\\textbf{{类型}}: {snapshot.get("type", "N/A")} \\\\',
            f'\\textbf{{难度}}: {snapshot.get("difficulty", "N/A")} \\\\',
        ]

        if snapshot.get('score') is not None:
            lines.append(f'\\textbf{{分值}}: {snapshot.get("score")} 分 \\\\')

        lines.extend(['', '\\textbf{题干}:', ''])

        stem = snapshot.get('stem_latex') or snapshot.get('stem_text') or ''
        if stem:
            lines.extend([str(stem), ''])

        if snapshot.get('appendix'):
            lines.extend(['\\textbf{附录}:', str(snapshot.get('appendix')), ''])

        qtype = str(snapshot.get('type', '')).upper()
        if qtype in {'MCQ', 'SINGLE_CHOICE', 'MULTIPLE_CHOICE'}:
            options = self._extract_choice_options(content)
            if options:
                lines.extend(['\\textbf{选项}:', '\\begin{itemize}'])
                for key, text in options:
                    lines.append(f'\\item [{key}.] {text}')
                lines.extend(['\\end{itemize}', ''])

        stem_images = snapshot.get('stem_images', [])
        if isinstance(stem_images, list):
            for img in stem_images:
                if isinstance(img, dict):
                    img_id = str(img.get('image_id') or '')
                    if img_id in downloaded_images:
                        lines.extend([f'\\includegraphics[width=0.5\\textwidth]{{{downloaded_images[img_id]}}}', ''])

        return lines

    @staticmethod
    def _extract_choice_options(content: Dict) -> List[tuple[str, str]]:
        options = content.get('options')
        parsed: List[tuple[str, str]] = []

        if isinstance(options, list):
            for idx, opt in enumerate(options):
                if isinstance(opt, dict):
                    key = str(opt.get('key') or opt.get('label') or chr(ord('A') + idx)).strip()
                    text = str(opt.get('text') or opt.get('content') or '').strip()
                elif isinstance(opt, str):
                    key = chr(ord('A') + idx)
                    text = opt.strip()
                else:
                    continue
                if text:
                    parsed.append((key, text))
            if parsed:
                return parsed

        if isinstance(options, dict):
            for key, value in options.items():
                text = str(value or '').strip()
                if text:
                    parsed.append((str(key).strip(), text))
            if parsed:
                return parsed

        choices = content.get('choices')
        if isinstance(choices, str):
            for line in choices.splitlines():
                raw = line.strip()
                if not raw:
                    continue
                match = re.match(r'^([A-Za-z])[\.\、\)\s]+(.+)$', raw)
                if match:
                    parsed.append((match.group(1).upper(), match.group(2).strip()))
                else:
                    key = chr(ord('A') + len(parsed))
                    parsed.append((key, raw))

        return parsed

    def _calculate_sha256(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


async def main_worker_loop(worker_id: str):
    logger.info('Starting worker %s', worker_id)
    worker = ExportWorker(worker_id)

    while True:
        try:
            async for db in get_db():
                await worker.maintenance_tick(db)
                job = await fetch_next_job(db, worker_id=worker_id, job_types=[JobType.EXPORT])
                if job:
                    await worker.process_job(db, job)
                else:
                    break
        except Exception as exc:
            logger.exception('Error in worker loop: %s', exc)

        await asyncio.sleep(settings.EXPORT_WORKER_POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Background job worker')
    parser.add_argument('--worker-id', default='worker-1', help='Worker identifier')
    args = parser.parse_args()

    try:
        asyncio.run(main_worker_loop(args.worker_id))
    except KeyboardInterrupt:
        logger.info('Worker stopped by user')
