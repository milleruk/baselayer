"""AsyncPelotonClient prototype (aiohttp-based).

This is a minimal async HTTP client scaffold for Peloton endpoints.
It is a prototype to use when converting synchronous fetches to async/batched calls.

Note: `aiohttp` must be added to `requirements.txt` and the runtime image
must install it to actually use this class.
"""
try:
    import aiohttp
except Exception:  # pragma: no cover - aiohttp may not be installed yet
    aiohttp = None


class AsyncPelotonClient:
    def __init__(self, session=None, base_url="https://api.onepeloton.com", timeout=30, headers=None, cookies=None):
        self._session = session
        self._own_session = False
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        # Optional headers/cookies to pass to aiohttp session (useful for auth)
        self.headers = headers or {}
        self.cookies = cookies or None

    async def __aenter__(self):
        if self._session is None:
            if aiohttp is None:
                raise RuntimeError("aiohttp is not installed; add it to requirements to use AsyncPelotonClient")
            # Propagate optional headers and cookies to the aiohttp session
            session_kwargs = {}
            if self.headers:
                session_kwargs['headers'] = self.headers
            if self.cookies:
                session_kwargs['cookies'] = self.cookies
            self._session = aiohttp.ClientSession(**session_kwargs)
            self._own_session = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._own_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def _get(self, path, params=None, headers=None):
        if aiohttp is None:
            raise RuntimeError("aiohttp is not installed; add it to requirements to use AsyncPelotonClient")
        url = f"{self.base_url}{path}"
        async with self._session.get(url, params=params, headers=headers, timeout=self.timeout) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def fetch_ride_details(self, ride_id):
        """Fetch ride details for a given Peloton ride id.

        Example endpoint path is a best-effort placeholder — update to match
        the actual API used elsewhere in the codebase when integrating.
        """
        return await self._get(f"/api/ride/{ride_id}")

    async def fetch_workout(self, workout_id):
        return await self._get(f"/api/workout/{workout_id}")

    async def fetch_performance_graph(self, workout_id, every_n=5):
        params = {"every_n": every_n}
        return await self._get(f"/api/workout/{workout_id}/performance_graph", params=params)
