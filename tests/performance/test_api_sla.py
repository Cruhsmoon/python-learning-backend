"""
Response time SLA assertions for all API endpoints.

Run:
    pytest tests/performance/test_api_sla.py -m performance -v
"""
import pytest

pytestmark = [pytest.mark.performance, pytest.mark.asyncio]


class TestAuthSLA:
    async def test_login(self, async_client, assert_sla):
        await assert_sla(
            async_client.post,
            "/auth/login",
            json={"username": "testuser", "password": "testpass"},
            sla_key="POST /auth/login",
        )

    async def test_login_invalid_credentials(self, async_client, assert_sla):
        await assert_sla(
            async_client.post,
            "/auth/login",
            json={"username": "nobody", "password": "wrong"},
            sla_key="POST /auth/login",
        )


class TestUsersSLA:
    async def test_get_me(self, async_client, auth_headers, assert_sla):
        await assert_sla(
            async_client.get,
            "/users/me",
            headers=auth_headers,
            sla_key="GET /users/me",
        )

    async def test_get_users(self, async_client, auth_headers, assert_sla):
        await assert_sla(
            async_client.get,
            "/users",
            headers=auth_headers,
            sla_key="GET /users",
        )

    async def test_create_user(self, async_client, assert_sla):
        await assert_sla(
            async_client.post,
            "/users",
            json={"name": "Perf User", "email": "perf@test.com"},
            sla_key="POST /users",
        )


class TestAdminSLA:
    async def test_admin_list_users(self, async_client, assert_sla):
        login = await async_client.post(
            "/auth/login",
            json={"username": "admin", "password": "adminpass"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        await assert_sla(
            async_client.get,
            "/admin/users",
            headers=headers,
            sla_key="GET /admin/users",
        )
