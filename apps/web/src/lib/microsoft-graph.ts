import "server-only";

import { getServerEnv, requireServerEnv } from "@/lib/server-env";

function getGraphBaseUrl() {
  return (
    getServerEnv("MICROSOFT_GRAPH_BASE_URL")?.trim().replace(/\/+$/, "") ||
    "https://graph.microsoft.com/v1.0"
  );
}

async function getAccessToken() {
  const tenantId = requireServerEnv("MICROSOFT_TENANT_ID");
  const clientId = requireServerEnv("MICROSOFT_CLIENT_ID");
  const clientSecret = requireServerEnv("MICROSOFT_CLIENT_SECRET");
  const scope =
    getServerEnv("MICROSOFT_GRAPH_SCOPE")?.trim() ||
    "https://graph.microsoft.com/.default";

  const response = await fetch(
    `https://login.microsoftonline.com/${encodeURIComponent(tenantId)}/oauth2/v2.0/token`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        grant_type: "client_credentials",
        scope,
      }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Microsoft token request failed: ${response.status} ${errorText}`);
  }

  const payload = (await response.json()) as { access_token?: string };
  if (!payload.access_token) {
    throw new Error("Microsoft token response did not include an access token.");
  }

  return payload.access_token;
}

export async function fetchGraphAttachmentContent(args: {
  mailboxAddress: string;
  messageId: string;
  attachmentId: string;
}) {
  const accessToken = await getAccessToken();
  const response = await fetch(
    `${getGraphBaseUrl()}/users/${encodeURIComponent(args.mailboxAddress)}/messages/${encodeURIComponent(args.messageId)}/attachments/${encodeURIComponent(args.attachmentId)}/$value`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: "application/octet-stream",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Graph attachment download failed: ${response.status} ${errorText}`,
    );
  }

  return response;
}
