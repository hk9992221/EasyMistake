"""Import legacy grading records for one explicitly selected account."""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo
from sqlalchemy import select
from api.core.config import settings
from api.core.database import AsyncSessionLocal
from api.models.user import User
from api.models.grading_record import GradingRecord
from api.api.v1.simple_grading import GradingRecordCreate


async def import_records(db, file: Path, user_email: str):
    user = (await db.execute(select(User).where(User.email == user_email, User.is_active.is_(True)))).scalar_one_or_none()
    if user is None:
        raise ValueError("Active target account not found")
    records = json.loads(file.read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("Expected a JSON array")
    count = 0
    for record in records:
        payload = GradingRecordCreate.model_validate(record)
        raw_id = str(record["id"])
        try:
            record_id = UUID(raw_id)
        except ValueError:
            record_id = uuid5(NAMESPACE_URL, "easymistake:grading:" + raw_id)
        existing = await db.get(GradingRecord, record_id)
        if existing:
            if existing.user_id != user.id:
                raise ValueError("Record already belongs to another account")
            continue
        created = datetime.fromisoformat(record["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=ZoneInfo(settings.APP_TIMEZONE))
        db.add(GradingRecord(id=record_id, user_id=user.id, created_at=created.astimezone(timezone.utc), **payload.model_dump()))
        await db.flush()
        count += 1
    return count


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--user-email", required=True)
    args = parser.parse_args()
    async with AsyncSessionLocal() as db, db.begin():
        count = await import_records(db, args.file, args.user_email)
    print(f"Imported {count} records; source file unchanged")


if __name__ == "__main__":
    asyncio.run(main())
