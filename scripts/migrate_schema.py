#!/usr/bin/env python3
"""Idempotent schema migration for the SOC platform.

Applies every structural change required by the current models onto the
target database, so fresh and existing deployments converge to the same
state. Safe to run multiple times.

Handles:
1. ORM tables (via SQLAlchemy `create_all(..., checkfirst=True)`), which
   covers tenants, users, roles, events, alerts, incidents, agent runs,
   agent skills, knowledge documents and agent memories.
2. New columns on pre-existing tables (`normalized_events`, `alerts`) that
   were introduced after the initial schema (detected at runtime).
3. The pgvector extension and `vector_chunks` table with HNSW index.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.core.config import get_settings
from app.domain import models  # noqa: F401  registers all ORM models
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine as db_engine
from app.infrastructure.vector.pgvector_client import initialize_vector_schema

COLUMN_DEFS = {
    "normalized_events": [
        "data_source_id uuid",
        "event_category varchar(80)",
        "event_class integer",
        "activity_id integer",
        "severity varchar(32)",
        "username varchar(255)",
        "source_port integer",
        "destination_port integer",
        "protocol varchar(32)",
        "hostname varchar(255)",
        "process_name varchar(255)",
        "command_line varchar(4096)",
        "file_hash_md5 varchar(32)",
        "file_hash_sha1 varchar(40)",
        "file_hash_sha256 varchar(64)",
        "domain varchar(255)",
        "url varchar(2048)",
        "cloud_identity varchar(255)",
        "cloud_resource varchar(255)",
        "authentication_result varchar(64)",
        "correlation_key varchar(255)",
        "session_id varchar(255)",
    ],
    "alerts": [
        "detection_rule_id varchar(255)",
        "correlation_key varchar(512)",
        "source_ip varchar(64)",
        "destination_ip varchar(64)",
        "actor varchar(255)",
        "raw_event_id uuid",
        "normalized_event_id uuid",
        "incident_id uuid",
        "confidence numeric(5,4)",
        "risk_explanation text",
        "first_seen_at timestamptz",
        "last_seen_at timestamptz",
        "occurrence_count integer DEFAULT 1",
    ],
}


async def migrate() -> None:
    async with db_engine.begin() as conn:
        # 1. ORM tables
        await conn.run_sync(Base.metadata.create_all)

        # 2. Missing columns on existing tables
        tables = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        existing = {row[0] for row in tables}
        for table, columns in COLUMN_DEFS.items():
            if table not in existing:
                continue
            present = {
                row[0]
                for row in await conn.execute(
                    text(
                        f"SELECT column_name FROM information_schema.columns "
                        f"WHERE table_schema = 'public' AND table_name = '{table}'"
                    )
                )
            }
            for column in columns:
                name = column.split(" ", 1)[0]
                if name in present:
                    continue
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column}"))

        # 3. pgvector schema (extension + vector_chunks + HNSW index)
        await initialize_vector_schema(conn)

    await db_engine.dispose()
    print("schema migration applied", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(migrate())
