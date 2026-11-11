"""One-time empty-database administrator bootstrap; input is private stdin JSON."""
import asyncio
import json
import re
import sys
import uuid

from sqlalchemy import func, select, text

from app.models import AuditLog, Permission, Role, User
from app.modules.auth.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from app.modules.auth.security import hash_password
from app.shared.database.session import get_sessionmaker
from app.shared.domain.enums import ActorType


async def main():
    values = json.load(sys.stdin)
    username, password = values['username'], values['password']
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{3,40}', username) or not 12 <= len(password.encode()) <= 72:
        raise ValueError('Invalid administrator credentials')
    async with get_sessionmaker()() as session, session.begin():
        await session.execute(text('SELECT pg_advisory_xact_lock(830031)'))
        if await session.scalar(select(func.count()).select_from(User)):
            raise ValueError('Bootstrap requires a database with no users')
        # Refuse partial/existing RBAC rather than silently changing permissions.
        if await session.scalar(select(func.count()).select_from(Role)):
            raise ValueError('Bootstrap requires an empty role catalogue')
        if await session.scalar(select(func.count()).select_from(Permission)):
            raise ValueError('Bootstrap requires an empty permission catalogue')
        permissions = {code: Permission(code=code, description=description)
                       for code, description in ALL_PERMISSIONS.items()}
        session.add_all(permissions.values())
        roles = {code: Role(code=code, name=code.replace('_', ' ').title(),
                           permissions=[permissions[p] for p in codes])
                 for code, codes in DEFAULT_ROLE_PERMISSIONS.items()}
        session.add_all(roles.values())
        admin = User(username=username, full_name='Server administrator',
                     hashed_password=hash_password(password), roles=[roles['ADMIN']], actor_type=ActorType.USER)
        session.add(admin)
        await session.flush()
        session.add(AuditLog(actor_type=ActorType.SYSTEM, actor_label='replica-bootstrap',
                            event_type='ADMIN_BOOTSTRAPPED', entity_type='User', entity_id=str(admin.id),
                            action='CREATE', reason='First administrator on a fresh replica',
                            after_value={'username': username, 'role_codes': ['ADMIN']},
                            correlation_id=str(uuid.uuid4())))


if __name__ == '__main__':
    asyncio.run(main())
