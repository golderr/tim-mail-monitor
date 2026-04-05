import { Fragment } from "react";

import {
  toggleThreadUrgencyAction,
  updateThreadReviewStateAction,
} from "@/app/(app)/thread-actions";
import { AdminThreadOverrideForm } from "@/components/admin-thread-override-form";
import type {
  DashboardName,
  DashboardThread,
  ThreadMessage,
} from "@/lib/dashboard-data";

const EVENT_LABELS: Record<string, string> = {
  deadline: "Deadline",
  draft_needed: "Draft Needed",
  meeting_request: "Meeting Request",
  scope_change: "Scope Change",
  client_materials: "Client Materials",
  status_request: "Status Request",
  commitment: "Commitment",
  cancellation_pause: "Cancellation/Pause",
  proposal_request: "Proposal Request",
  new_project: "New Project",
};

const REVIEW_STATE_LABELS: Record<string, string> = {
  open: "Open",
  handled: "Handled",
  disregard: "Disregard",
};

const REPLY_STATE_LABELS: Record<string, string> = {
  unanswered: "Unanswered",
  answered: "Answered",
  partial_answer: "Partial Answer",
  answered_offline: "Answered Offline",
};

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Los_Angeles",
    timeZoneName: "short",
  }).format(new Date(value));
}

function formatDirection(value: "sent" | "received" | null) {
  if (value === "sent") {
    return "Sent";
  }
  if (value === "received") {
    return "Received";
  }
  return "Unknown";
}

function badgeTone(tag: string) {
  if (
    tag === "deadline" ||
    tag === "draft_needed" ||
    tag === "cancellation_pause"
  ) {
    return "status-pill--danger";
  }

  if (
    tag === "scope_change" ||
    tag === "meeting_request" ||
    tag === "status_request"
  ) {
    return "status-pill--warning";
  }

  return "status-pill--neutral";
}

function actionOptionsForDashboard(dashboard: DashboardName) {
  switch (dashboard) {
    case "needs_attention":
      return [
        { label: "Handled", value: "handled" },
        { label: "Disregard", value: "disregard" },
      ];
    case "closed":
      return [{ label: "Reopen", value: "open" }];
    case "not_promoted":
      return [{ label: "Move To Open", value: "open" }];
    case "admin":
      return [
        { label: "Open", value: "open" },
        { label: "Handled", value: "handled" },
        { label: "Disregard", value: "disregard" },
      ];
  }
}

function renderRecipients(message: ThreadMessage) {
  if (message.recipients.length === 0) {
    return ["No recipients recorded"];
  }

  return message.recipients.map((recipient) => {
    const label = recipient.displayName || recipient.email;
    return `${recipient.recipientType.toUpperCase()}: ${label}`;
  });
}

export function ThreadList({
  items,
  emptyMessage,
  dashboard,
  returnTo,
}: Readonly<{
  items: DashboardThread[];
  emptyMessage: string;
  dashboard: DashboardName;
  returnTo: string;
}>) {
  if (items.length === 0) {
    return (
      <section className="panel">
        <p className="empty-state">{emptyMessage}</p>
      </section>
    );
  }

  const actions = actionOptionsForDashboard(dashboard);

  return (
    <section className="thread-list">
      {items.map((item) => {
        const visibleTags = item.eventTags.slice(0, 2);
        const remainingTagCount = Math.max(item.eventTags.length - visibleTags.length, 0);
        const hiddenTags = item.eventTags.slice(2);
        const hiddenTagsLabel = hiddenTags
          .map((tag) => EVENT_LABELS[tag] ?? tag)
          .join(", ");
        const showReviewState = !(dashboard === "needs_attention" && item.reviewState === "open");

        return (
          <article className="thread-card" key={item.id}>
            <div className="thread-card__header">
              <div className="thread-card__title-block">
                <p className="thread-card__client">
                  {item.clientNames.length > 0
                    ? item.clientNames.join(", ")
                    : item.clientDisplayName || "Unresolved client"}
                </p>
                <p className="thread-card__people">
                  {item.externalCorrespondents.length > 0
                    ? item.externalCorrespondents.join(", ")
                    : "No external names identified"}
                </p>
                {item.internalParticipants.length > 0 ? (
                  <p className="thread-card__internal">
                    TCG: {item.internalParticipants.join(", ")}
                  </p>
                ) : null}
                <h2>{item.title}</h2>
              </div>

              <div className="thread-card__badges">
                {visibleTags.map((tag) => (
                  <span className={`status-pill ${badgeTone(tag)}`} key={tag}>
                    {EVENT_LABELS[tag] ?? tag}
                  </span>
                ))}
                {remainingTagCount > 0 ? (
                  <span
                    className="status-pill status-pill--neutral"
                    title={hiddenTagsLabel}
                  >
                    +{remainingTagCount} more
                  </span>
                ) : null}
                {showReviewState ? (
                  <span className="status-pill status-pill--neutral">
                    {REVIEW_STATE_LABELS[item.reviewState] ?? item.reviewState}
                  </span>
                ) : null}
                <span
                  className={`status-pill ${
                    item.replyState === "unanswered"
                      ? "status-pill--warning"
                      : "status-pill--neutral"
                  }`}
                >
                  {REPLY_STATE_LABELS[item.replyState] ?? item.replyState}
                </span>
              </div>
            </div>

            {item.cardHeader ? (
              <p className="thread-card__headline">{item.cardHeader}</p>
            ) : null}

            <div className="thread-card__meta-grid">
              <span>Project: {item.projectNumber ?? "Unknown"}</span>
              <span>{item.messageCount} messages</span>
            </div>

            <p className="thread-card__snippet">
              {item.summary || "No summary or snippet is stored yet for this thread."}
            </p>

            <details className="thread-card__details-panel">
              <summary>Expand full thread</summary>
              <div className="thread-card__messages">
                {item.messages.map((message, index) => (
                  <Fragment key={message.id}>
                    {index > 0 ? <hr className="thread-card__message-divider" /> : null}
                    <article className="message-card">
                      <div className="message-card__header">
                        <div className="message-card__header-main">
                          <strong className="message-card__subject">
                            {message.subject || "(No subject)"}
                          </strong>
                          <p className="message-card__sender">
                            {message.senderName || message.senderEmail || "Unknown sender"}
                          </p>
                        </div>
                        <div className="message-card__header-side">
                          <span className="status-pill status-pill--neutral">
                            {message.direction === "sent" ? "Sent" : "Received"}
                          </span>
                          <p className="message-card__date">
                            {formatTimestamp(message.timestamp)}
                          </p>
                        </div>
                      </div>
                      <div className="message-card__recipients">
                        {renderRecipients(message).map((line) => (
                          <p key={line}>{line}</p>
                        ))}
                      </div>
                      <pre className="message-card__body">
                        {message.bodyText || "No message body stored."}
                      </pre>
                    </article>
                  </Fragment>
                ))}
              </div>
            </details>

            <div className="thread-card__footer">
              <div className="thread-card__footer-left">
                <span className="thread-card__timestamp">
                  {formatDirection(item.latestCorrespondenceDirection)} |{" "}
                  {formatTimestamp(item.latestCorrespondenceAt)}
                </span>
              </div>

              <div className="thread-card__footer-right">
                <div className="thread-card__actions">
                  {actions.map((action) => (
                    <form action={updateThreadReviewStateAction} key={action.value}>
                      <input type="hidden" name="threadId" value={item.id} />
                      <input type="hidden" name="reviewState" value={action.value} />
                      <input type="hidden" name="returnTo" value={returnTo} />
                      <button
                        className={
                          action.value === "open" ? "primary-button" : "ghost-button"
                        }
                        type="submit"
                      >
                        {action.label}
                      </button>
                    </form>
                  ))}
                </div>

                <form action={toggleThreadUrgencyAction}>
                  <input type="hidden" name="threadId" value={item.id} />
                  <input type="hidden" name="returnTo" value={returnTo} />
                  <button
                    className={`status-pill thread-card__urgent-toggle ${
                      item.isUrgent
                        ? "status-pill--danger"
                        : "thread-card__urgent-toggle--inactive"
                    }`}
                    type="submit"
                  >
                    Urgent
                  </button>
                </form>
              </div>
            </div>

            {dashboard === "admin" ? (
              <AdminThreadOverrideForm item={item} returnTo={returnTo} />
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
