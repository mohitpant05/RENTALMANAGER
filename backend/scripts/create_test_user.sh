#!/bin/bash
# Quick script to create a test user in the backend container
# Usage: docker compose exec backend bash /app/scripts/create_test_user.sh

python -c "
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from uuid import uuid4
import bcrypt

async def main():
    engine = create_async_engine('postgresql+asyncpg://rentmanager:rentmanager_dev@postgres:5432/rentmanager')
    
    async with AsyncSession(engine) as session:
        # Check existing
        result = await session.exec(select(User).where(User.email == 'test@rentmanager.local'))
        if result.first():
            print('Test user already exists: test@rentmanager.local / testpassword123')
            return
            
        # Get tenant
        from app.core.tenancy.models import Tenant
        result = await session.exec(select(Tenant).limit(1))
        tenant = result.first()
        
        if not tenant:
            print('No tenant found!')
            return
            
        # Create user
        from app.core.auth.models import User
        user = User(
            id=uuid4(),
            email='test@rentmanager.local',
            password_hash=bcrypt.hashpw('testpassword123'.encode(), bcrypt.gensalt()).decode(),
            full_name='Test User',
            is_active=True,
            is_verified=True,
            user_type='admin',
        )
        session.add(user)
        await session.commit()
        
        print('=' * 50)
        print('TEST USER CREATED')
        print('=' * 50)
        print('Email:    test@rentmanager.local')
        print('Password: testpassword123')
        print('=' * 50)
        
    await engine.dispose()

from app.core.auth.models import User
asyncio.run(main())
"
