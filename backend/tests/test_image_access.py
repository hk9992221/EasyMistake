import threading

import pytest

from api.core.deps import get_current_user
from api.core.security import create_access_token
from api.main import app
from api.models import Image, UserRole
from api.services.image_service import image_service


@pytest.mark.parametrize('auth, status', [
    ('owner', 200), ('admin', 200), ('foreign', 403),
    ('inactive', 401), ('query_token', 401), ('none', 401),
])
async def test_image_file_requires_header_auth_and_private_cache(db, users, client, monkeypatch, auth, status):
    owner, other = users
    image = Image(user_id=owner.id, object_key='private.png', sha256='0' * 64,
                  mime='image/png', size_bytes=8)
    db.add(image)
    if auth == 'admin':
        other.role = UserRole.ADMIN
    if auth == 'inactive':
        owner.is_active = False
    await db.commit()
    app.dependency_overrides.pop(get_current_user)
    token_user = other if auth in ('admin', 'foreign') else owner
    token = create_access_token({'sub': str(token_user.id)})
    url = f'/api/v1/images/{image.id}/file'
    headers = {}
    if auth == 'query_token':
        url += f'?token={token}'
    elif auth != 'none':
        headers['Authorization'] = f'Bearer {token}'
    threads = []
    main_thread = threading.get_ident()

    def fetch_image(key):
        assert key == 'private.png'
        threads.append(threading.get_ident())
        return b'png-data'

    monkeypatch.setattr(image_service, 'fetch_image_bytes', fetch_image)
    response = await client.get(url, headers=headers)
    assert response.status_code == status, response.text
    if status == 200:
        assert response.content == b'png-data'
        assert response.headers['cache-control'] == 'private, no-store'
        assert 'authorization' in {part.strip().lower() for part in response.headers['vary'].split(',')}
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert len(threads) == 1 and threads[0] != main_thread
    else:
        assert threads == []


async def test_storage_failure_does_not_expose_internal_details(db, users, client, monkeypatch):
    image = Image(user_id=users[0].id, object_key='missing.png', sha256='0' * 64,
                  mime='image/png', size_bytes=8)
    db.add(image)
    await db.commit()

    def unavailable(key):
        raise RuntimeError('private storage credentials and endpoint')

    monkeypatch.setattr(image_service, 'fetch_image_bytes', unavailable)
    response = await client.get(f'/api/v1/images/{image.id}/file')
    assert response.status_code == 404
    assert 'private storage' not in response.text
