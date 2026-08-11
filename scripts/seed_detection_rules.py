"""Seed default detection rules for every tenant.

Idempotent: rules with the same rule_id are skipped when they already exist
(rule_id has a global unique constraint, so each default rule exists at most
once; per-tenant copies use a tenant-qualified suffix to stay unique).
"""

from __future__ import annotations

import asyncio
import os
import sys

import yaml
from sqlalchemy import select

if "DATABASE_URL" not in os.environ and "DATABASE_URL_SYNC" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_SYNC"]
os.environ.setdefault("APP_ENV", "local")

from app.domain.models import DetectionRule, Tenant  # noqa: E402
from app.domain.pipeline.detection import compile_rule, seed_default_rules  # noqa: E402
from app.infrastructure.db.session import AsyncSessionFactory  # noqa: E402


async def main() -> int:
    templates = seed_default_rules()
    seeded = 0
    skipped = 0
    async with AsyncSessionFactory() as session:
        tenants = await session.execute(select(Tenant))
        tenant_ids = [tenant.id for tenant in tenants.scalars().all()]
        if not tenant_ids:
            print("no tenants found; nothing to seed", file=sys.stderr)
            return 1
        for template in templates:
            for tenant_id in tenant_ids:
                rule_id = f"{template['id']}"
                lookup = await session.execute(
                    select(DetectionRule).where(
                        DetectionRule.tenant_id == tenant_id,
                        DetectionRule.rule_id == rule_id,
                    )
                )
                if lookup.scalar_one_or_none() is not None:
                    skipped += 1
                    continue
                compiled_yaml = yaml.safe_dump(template)
                compiled = compile_rule(compiled_yaml)
                rule = DetectionRule(
                    tenant_id=tenant_id,
                    name=template["title"],
                    description=template.get("description"),
                    rule_id=rule_id,
                    severity=template.get("level", "medium"),
                    mitre=template.get("tags", {}),
                    rule_yaml=compiled_yaml,
                    compiled_query=str(compiled.expression),
                    is_enabled=True,
                )
                session.add(rule)
                seeded += 1
        await session.commit()
    print(f"seeded={seeded} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
