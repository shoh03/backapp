"""일반 회원 쿠키 세션/재발급 회귀 검사. 실제 DB·Redis·OAuth는 사용하지 않습니다."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from app.api.auth_api import router as auth_router
from app.api.user_api import router as user_router
from app.schema.user_schema import UserClaimDTO, UserResponseDTO
from app.service.auth_service import get_auth_service
from app.service.user_service import get_user_service
from app.util.jwt_token_util import generate_access_token


class UserSessionApiTests(unittest.TestCase):
    def setUp(self):
        self.key = patch('app.util.jwt_token_util.SECRET_KEY', 'isolated-session-test-key')
        self.algorithm = patch('app.util.jwt_token_util.ALGORITHM', 'HS256')
        self.key.start()
        self.algorithm.start()
        self.profile = UserResponseDTO(id=7, user_name='검사 사용자', user_provider='KAKAO',
            user_provider_id='test-provider', user_email='test@example.invalid', user_nickname='검사',
            user_phone='01000000000', user_status=True, user_created_at=datetime.now(timezone.utc))
        self.users = SimpleNamespace(get_user_by_id=AsyncMock(return_value=self.profile))
        self.auth = SimpleNamespace(is_blacklisted_token=AsyncMock(return_value=False),
                                    refresh=AsyncMock(return_value='new-access-token'))
        app = FastAPI()
        app.include_router(user_router, prefix='/users')
        app.include_router(auth_router, prefix='/auth')
        app.dependency_overrides[get_user_service] = lambda: self.users
        app.dependency_overrides[get_auth_service] = lambda: self.auth
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.key.stop()
        self.algorithm.stop()

    def login_cookie(self):
        self.client.cookies.set('access_token', generate_access_token(UserClaimDTO(id=7, user_provider='KAKAO')))

    def test_me_without_cookie_is_unauthorized(self):
        self.assertEqual(self.client.get('/users/me').status_code, 401)
        self.users.get_user_by_id.assert_not_awaited()

    def test_me_returns_only_the_signed_in_user(self):
        self.login_cookie()
        response = self.client.get('/users/me?id=999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['user_name'], '검사 사용자')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.users.get_user_by_id.assert_awaited_once_with(7)

    def test_invalid_and_expired_access_are_rejected(self):
        expired = jwt.encode({'id':7, 'user_provider':'KAKAO', 'exp':datetime.now(timezone.utc)-timedelta(seconds=5)},
                             'isolated-session-test-key', algorithm='HS256')
        for token in ['invalid', expired]:
            self.client.cookies.set('access_token', token)
            self.assertEqual(self.client.get('/users/me').status_code, 401)
        self.users.get_user_by_id.assert_not_awaited()

    def test_blacklisted_access_is_rejected(self):
        self.login_cookie()
        self.auth.is_blacklisted_token.return_value = True
        self.assertEqual(self.client.get('/users/me').status_code, 401)
        self.users.get_user_by_id.assert_not_awaited()

    def test_inactive_user_is_rejected(self):
        self.login_cookie()
        self.profile.user_status = False
        self.assertEqual(self.client.get('/users/me').status_code, 403)

    def test_refresh_works_without_an_access_cookie(self):
        self.client.cookies.set('refresh_token', 'test-refresh')
        response = self.client.get('/auth/refresh')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.auth.refresh.assert_awaited_once_with('test-refresh')
        self.assertIn('access_token=new-access-token', response.headers['set-cookie'])

    def test_missing_refresh_cannot_issue_access(self):
        response = self.client.get('/auth/refresh')
        self.assertFalse(response.json()['success'])
        self.auth.refresh.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
