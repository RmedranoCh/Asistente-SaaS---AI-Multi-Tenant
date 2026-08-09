class TestHealth:
    async def test_health_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["version"]

    async def test_api_v1_prefix_mounted(self, client):
        resp = await client.get("/api/v1/mock/inbox")
        assert resp.status_code == 200