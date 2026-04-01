"""Microsoft Graph mailbox polling client."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator

import msal
import requests

from tim_mail_monitor_worker.config import Settings


class GraphClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._app = msal.ConfidentialClientApplication(
            client_id=settings.microsoft_client_id,
            authority=(
                "https://login.microsoftonline.com/"
                f"{settings.microsoft_tenant_id}"
            ),
            client_credential=settings.microsoft_client_secret,
        )
        self._session = requests.Session()

    def close(self) -> None:
        self._session.close()

    def _get_access_token(self) -> str:
        result = self._app.acquire_token_for_client(
            scopes=[self.settings.microsoft_graph_scope]
        )
        access_token = result.get("access_token")
        if not access_token:
            raise RuntimeError(
                f"Graph token acquisition failed: {result.get('error_description') or result}"
            )
        return access_token

    def _request(
        self, method: str, url: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response = self._session.request(
            method,
            url,
            params=params,
            timeout=self.settings.graph_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self._get_access_token()}",
                "Accept": "application/json",
                'Prefer': 'outlook.body-content-type="text"',
            },
        )
        response.raise_for_status()
        return response.json()

    def iter_messages(
        self,
        *,
        mailbox_address: str,
        folder_name: str,
        since: datetime | None,
        max_messages: int,
    ) -> Iterator[dict[str, Any]]:
        time_field = "sentDateTime" if folder_name == "SentItems" else "receivedDateTime"
        params: dict[str, Any] = {
            "$top": min(max_messages, self.settings.graph_message_page_size),
            "$orderby": f"{time_field} desc",
            "$select": ",".join(
                [
                    "id",
                    "internetMessageId",
                    "conversationId",
                    "conversationIndex",
                    "parentFolderId",
                    "subject",
                    "bodyPreview",
                    "body",
                    "createdDateTime",
                    "receivedDateTime",
                    "sentDateTime",
                    "lastModifiedDateTime",
                    "from",
                    "sender",
                    "toRecipients",
                    "ccRecipients",
                    "bccRecipients",
                    "replyTo",
                    "hasAttachments",
                    "isRead",
                    "isDraft",
                    "importance",
                    "categories",
                    "flag",
                    "inferenceClassification",
                    "webLink",
                ]
            ),
        }
        if since is not None:
            params["$filter"] = f"{time_field} ge {since.isoformat()}"

        next_url = (
            f"{self.settings.microsoft_graph_base_url}/users/"
            f"{mailbox_address}/mailFolders/{folder_name}/messages"
        )
        yielded = 0

        while next_url and yielded < max_messages:
            payload = self._request("GET", next_url, params=params)
            params = None

            for message in payload.get("value", []):
                yield message
                yielded += 1
                if yielded >= max_messages:
                    break

            next_url = payload.get("@odata.nextLink")

    def get_attachments(
        self, *, mailbox_address: str, message_id: str
    ) -> list[dict[str, Any]]:
        payload = self._request(
            "GET",
            (
                f"{self.settings.microsoft_graph_base_url}/users/"
                f"{mailbox_address}/messages/{message_id}/attachments"
            ),
            params={
                "$select": ",".join(
                    [
                        "id",
                        "name",
                        "contentType",
                        "size",
                        "isInline",
                        "contentId",
                        "lastModifiedDateTime",
                        "@odata.type",
                    ]
                )
            },
        )
        return list(payload.get("value", []))
