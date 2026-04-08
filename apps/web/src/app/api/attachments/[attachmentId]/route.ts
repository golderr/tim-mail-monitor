import { NextResponse } from "next/server";

import { getSessionIdentity } from "@/lib/auth";
import { fetchGraphAttachmentContent } from "@/lib/microsoft-graph";
import { query } from "@/lib/server-db";

type AttachmentRow = {
  id: string;
  download_eligible: boolean;
  download_policy: string;
  graph_attachment_id: string | null;
  name: string;
  content_type: string | null;
  size_bytes: string;
  is_inline: boolean;
  message_id: string;
  graph_message_id: string;
  thread_record_id: string;
  mailbox_address: string;
};

function downloadFilename(value: string | null | undefined) {
  const normalized = value?.trim();
  return normalized || "attachment";
}

function buildContentDisposition(filename: string) {
  return `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`;
}

async function loadAttachment(attachmentId: string) {
  const { rows } = await query<AttachmentRow>(
    `
      select
        a.id::text,
        a.download_eligible,
        a.download_policy,
        a.graph_attachment_id,
        a.name,
        a.content_type,
        a.size_bytes::text,
        a.is_inline,
        m.id::text as message_id,
        m.graph_message_id,
        tr.id::text as thread_record_id,
        mc.mailbox_address::text as mailbox_address
      from public.attachments a
      inner join public.messages m on m.id = a.message_id
      inner join public.thread_records tr on tr.id = m.thread_record_id
      inner join public.mailbox_configs mc on mc.id = tr.mailbox_config_id
      where a.id::text = $1
      limit 1
    `,
    [attachmentId],
  );

  return rows[0] ?? null;
}

async function logDownloadEvent(args: {
  attachment: AttachmentRow;
  userEmail: string;
  status: "success" | "denied" | "failed";
  errorText?: string;
}) {
  await query(
    `
      insert into public.attachment_download_events (
        attachment_id,
        message_id,
        thread_record_id,
        user_email,
        status,
        error_text
      )
      values ($1::uuid, $2::uuid, $3::uuid, $4, $5, $6)
    `,
    [
      args.attachment.id,
      args.attachment.message_id,
      args.attachment.thread_record_id,
      args.userEmail,
      args.status,
      args.errorText ?? null,
    ],
  );
}

export async function GET(
  request: Request,
  context: { params: Promise<{ attachmentId: string }> },
) {
  const session = await getSessionIdentity();
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (session.role !== "admin" && session.role !== "lead") {
    return new NextResponse("Forbidden", { status: 403 });
  }

  const { attachmentId } = await context.params;
  const attachment = await loadAttachment(attachmentId);
  if (!attachment) {
    return new NextResponse("Attachment not found.", { status: 404 });
  }

  if (
    !attachment.download_eligible ||
    attachment.is_inline ||
    !attachment.graph_attachment_id
  ) {
    await logDownloadEvent({
      attachment,
      userEmail: session.email,
      status: "denied",
      errorText: `Attachment is not downloadable. Policy: ${attachment.download_policy}`,
    });
    return new NextResponse("Attachment not found.", { status: 404 });
  }

  try {
    const graphResponse = await fetchGraphAttachmentContent({
      mailboxAddress: attachment.mailbox_address,
      messageId: attachment.graph_message_id,
      attachmentId: attachment.graph_attachment_id,
    });

    await logDownloadEvent({
      attachment,
      userEmail: session.email,
      status: "success",
    });

    const headers = new Headers();
    headers.set(
      "Content-Type",
      graphResponse.headers.get("content-type") ||
        attachment.content_type ||
        "application/octet-stream",
    );
    headers.set(
      "Content-Disposition",
      buildContentDisposition(downloadFilename(attachment.name)),
    );
    headers.set("Cache-Control", "private, no-store");
    headers.set("X-Content-Type-Options", "nosniff");

    const contentLength =
      graphResponse.headers.get("content-length") || attachment.size_bytes;
    if (contentLength) {
      headers.set("Content-Length", contentLength);
    }

    return new Response(graphResponse.body, {
      status: 200,
      headers,
    });
  } catch (error) {
    const errorText =
      error instanceof Error ? error.message : "Unknown attachment download failure.";
    await logDownloadEvent({
      attachment,
      userEmail: session.email,
      status: "failed",
      errorText,
    });
    return new NextResponse("Attachment download failed.", { status: 502 });
  }
}
