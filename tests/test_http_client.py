from bot.__main__ import build_http_client


async def test_build_http_client_ignores_environment_proxy_settings():
    client = build_http_client()

    try:
        assert client.trust_env is False
    finally:
        await client.aclose()
