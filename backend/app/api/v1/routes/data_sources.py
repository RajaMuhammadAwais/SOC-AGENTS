"""Data source management (spec section 11-13).

Data sources are tenant-scoped ingestion endpoints. Each data source
declares a connector type; the connector registry maps types to their
configuration schemas and parsers. Supported connectors:

- api_json      — push events via POST /ingestion/events (canonical JSON)
- cef           — ArcSight Common Event Format (RFC-5424-ish header + ext)
- syslog        — plain syslog lines parsed heuristically (best-effort)
- csv           — batch CSV upload with header mapping

Connector addition follows the documented registration pattern in
docs/architecture/connector-model.md: add a class to the registry and a
validation schema; parsers stay deterministic and tenant-isolated.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CursorPage, MessageResponse
from app.core.permissions import Principal, require_permission
from app.domain.models import DataSource
from app.infrastructure.db.session import get_db_session

logger = structlog.get_logger("data_sources")

router = APIRouter(prefix="/data-sources", tags=["data-sources"])

CEF_HEADER_PATTERN = re.compile(
    r"^(?P<version>Cef:0)\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<vversion>[^|]*)\|"
    r"(?P<signature_id>[^|]*)\|(?P<name>[^|]*)\|(?P<severity>[^|]*)\|(?P<extensions>.*)$"
)

CEF_KEY_VALUE_PATTERN = re.compile(r"(?P<key>[a-zA-Z][\w.]*)=(?P<value>(?:[^\\]|\\.)*?)(?=\s[a-zA-Z][\w.]*=|$)")


class ConnectorRegistry:
    """Deterministic registry mapping connector types to config schemas."""

    SCHEMAS: dict[str, dict[str, str]] = {
        "api_json": {"api_token": "str (required)"},
        "cef": {"listen_port": "int (optional, default 514)"},
        "syslog": {"listen_port": "int (optional, default 514)", "protocol": "tcp|udp"},
        "csv": {"delimiter": "str (optional, default ',')", "has_header": "bool (default true)"},
    }

    @classmethod
    def validate(cls, source_type: str, config: dict[str, Any]) -> None:
        if source_type not in cls.SCHEMAS:
            raise HTTPException(
                status_code=422,
                detail=f"unsupported connector type: {source_type}; supported: {sorted(cls.SCHEMAS)}",
            )
        if source_type == "api_json" and not str(config.get("api_token", "")).strip():
            raise HTTPException(status_code=422, detail="api_token is required for api_json connectors")


def parse_cef(raw_line: str) -> dict[str, Any] | None:
    """Parse an ArcSight CEF line into canonical-event-shaped fields.

    Mapping is intentionally limited to the fields the platform models;
    unmatched extensions are preserved under `cef_extensions`.
    """

    match = CEF_HEADER_PATTERN.match(raw_line.strip())
    if match is None:
        return None
    extensions: dict[str, str] = {}
    for matched in CEF_KEY_VALUE_PATTERN.finditer(match.group("extensions")):
        extensions[matched.group("key")] = matched.group("value").replace("\\|", "|").replace("\\=", "=")
    return {
        "event_type": f"cef:{match.group('signature_id')}",
        "vendor": match.group("vendor"),
        "product": match.group("product"),
        "name": match.group("name"),
        "raw_severity": match.group("severity"),
        "source_ip": extensions.get("src"),
        "source_port": extensions.get("spt"),
        "destination_ip": extensions.get("dst"),
        "destination_port": extensions.get("dpt"),
        "protocol": extensions.get("proto"),
        "username": extensions.get("suser") or extensions.get("duser"),
        "hostname": extensions.get("shost") or extensions.get("dhost"),
        "cef_extensions": extensions,
    }


def parse_syslog(raw_line: str) -> dict[str, Any] | None:
    """Best-effort heuristic syslog parse (no RFC enforcement)."""

    stripped = raw_line.strip()
    if not stripped:
        return None
    parts = stripped.split(None, 5)
    return {
        "event_type": "syslog:line",
        "raw_host": parts[0] if len(parts) > 0 else None,
        "raw_message": stripped,
    }


def parse_csv_batch(raw_text: str, delimiter: str = ",", has_header: bool = True) -> list[dict[str, Any]]:
    """Parse a CSV batch into event rows (header row becomes field names)."""

    reader = csv.DictReader(io.StringIO(raw_text), delimiter=delimiter or ",")
    if has_header and reader.fieldnames is None:
        raise ValueError("CSV has no header row")
    return [{key: str(value) for key, value in row.items() if value is not None} for row in reader]


@router.get("", tags=["data-sources"])
async def list_data_sources(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("data_sources:read")),
) -> CursorPage[dict[str, Any]]:
    sources = await session.execute(
        select(DataSource).where(DataSource.tenant_id == principal.tenant_id)
    )
    items = [
        {
            "id": str(source.id),
            "name": source.name,
            "source_type": source.source_type,
            "is_active": source.is_active,
            "created_at": source.created_at.isoformat(),
        }
        for source in sources.scalars().all()
    ]
    return CursorPage(items=items)


@router.post("", tags=["data-sources"])
async def create_data_source(
    payload: dict,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("data_sources:write")),
) -> dict[str, Any]:
    source_type = str(payload.get("source_type", "")).strip()
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 255:
        raise HTTPException(status_code=422, detail="name is required (max 255 chars)")
    ConnectorRegistry.validate(source_type, payload.get("config", {}))
    source = DataSource(
        tenant_id=principal.tenant_id,
        name=name,
        source_type=source_type,
        config=payload.get("config", {}),
        is_active=True,
    )
    session.add(source)
    await session.commit()
    return {
        "id": str(source.id),
        "name": source.name,
        "source_type": source.source_type,
        "is_active": source.is_active,
    }


@router.delete("/{source_id}", tags=["data-sources"])
async def delete_data_source(
    source_id: str,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("data_sources:write")),
) -> MessageResponse:
    from uuid import UUID

    source_result = await session.execute(
        select(DataSource).where(
            DataSource.tenant_id == principal.tenant_id,
            DataSource.id == UUID(source_id),
        )
    )
    source = source_result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="data source not found")
    await session.delete(source)
    await session.commit()
    return MessageResponse(message=f"data source {source_id} deleted")


@router.post("/{source_id}/upload", tags=["data-sources"])
async def upload_csv_events(
    source_id: str,
    file: UploadFile,
    batch_nonce: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("ingestion:write")),
) -> dict[str, Any]:
    """Upload a CSV batch of events for a csv-type data source."""

    from datetime import UTC, datetime
    from uuid import UUID

    from app.domain.pipeline.service import process_ingested_event

    source_result = await session.execute(
        select(DataSource).where(
            DataSource.tenant_id == principal.tenant_id,
            DataSource.id == UUID(source_id),
        )
    )
    source = source_result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="data source not found")
    if source.source_type != "csv":
        raise HTTPException(status_code=422, detail="upload only supported for csv connectors")
    if file.size is not None and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file exceeds 10 MiB")
    raw_text = (await file.read()).decode("utf-8", errors="replace")
    delimiter = str(source.config.get("delimiter", ","))
    rows = parse_csv_batch(raw_text, delimiter=delimiter)
    processed = 0
    for index, row in enumerate(rows):
        await process_ingested_event(
            session=session,
            tenant_id=principal.tenant_id,
            data_source_id=source.id,
            source_event_id=(
                f"csv:{source_id}:{batch_nonce}:{index}:{row.get('timestamp', index)}"
                if batch_nonce
                else f"csv:{source_id}:{index}:{row.get('timestamp', index)}"
            ),
            occurred_at=datetime.now(UTC),
            payload=row,
            principal=principal,
        )
        processed += 1
    await session.commit()
    return {"processed": processed}
