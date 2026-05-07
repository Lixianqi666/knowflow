import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@test.com", "password": "pass1234", "name": "New"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@test.com"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "password": "pass1234", "name": "Dup"},
    )
    assert resp.status_code == 200
    resp2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "password": "pass1234", "name": "Dup2"},
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@test.com", "password": "pass1234", "name": "Login"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "login@test.com", "password": "pass1234"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@test.com", "password": "pass1234", "name": "Wrong"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "wrong@test.com", "password": "badpassword"}
    )
    assert resp.status_code == 401
