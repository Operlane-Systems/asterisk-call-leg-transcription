"""Small, explicit ARI client used by the real-time call-leg pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote

import requests
import websockets


@dataclass(frozen=True)
class ARISettings:
    url: str
    username: str
    password: str
    app_name: str


class ARIClient:
    """Deliberately narrow ARI wrapper; helpers are always caller-owned."""

    def __init__(self, settings: ARISettings):
        self.base_url = settings.url.rstrip("/")
        self.auth = (settings.username, settings.password)
        self.app_name = settings.app_name
        username = quote(settings.username, safe="")
        password = quote(settings.password, safe="")
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.events_url = (
            f"{ws_base}/events?app={self.app_name}&subscribeAll=true&api_key={username}:{password}"
        )

    def _request(self, method: str, path: str, **params):
        response = requests.request(
            method, f"{self.base_url}{path}", auth=self.auth, params=params, timeout=10
        )
        response.raise_for_status()
        return response.json() if response.content else None

    def create_bridge(self, bridge_id: str) -> None:
        self._request("POST", f"/bridges/{bridge_id}", type="mixing")

    def destroy_bridge(self, bridge_id: str) -> None:
        try:
            self._request("DELETE", f"/bridges/{bridge_id}")
        except requests.RequestException:
            pass

    def add_to_bridge(self, bridge_id: str, channel_id: str) -> None:
        self._request("POST", f"/bridges/{bridge_id}/addChannel", channel=channel_id)

    def remove_from_bridge(self, bridge_id: str, channel_id: str) -> None:
        try:
            self._request("POST", f"/bridges/{bridge_id}/removeChannel", channel=channel_id)
        except requests.RequestException:
            pass

    def hangup(self, channel_id: str) -> None:
        try:
            self._request("DELETE", f"/channels/{channel_id}")
        except requests.RequestException:
            pass

    def snoop(self, target_channel_id: str, *, snoop_id: str, spy: str = "in") -> dict:
        return self._request(
            "POST",
            f"/channels/{target_channel_id}/snoop",
            app=self.app_name,
            spy=spy,
            snoopId=snoop_id,
        )

    def external_media(self, *, channel_id: str, host: str) -> dict:
        return self._request(
            "POST",
            "/channels/externalMedia",
            app=self.app_name,
            channelId=channel_id,
            external_host=host,
            format="ulaw",
            direction="both",
        )

    async def events(self):
        """Yield ARI events. The calling app decides which channels are call legs."""

        async with websockets.connect(self.events_url, ping_interval=20, ping_timeout=20) as websocket:
            async for raw in websocket:
                try:
                    yield json.loads(raw)
                except json.JSONDecodeError:
                    continue
