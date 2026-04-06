import { Fragment, type ReactNode } from "react";

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

const DISPLAY_TIME_ZONE = "America/Los_Angeles";
const TIMESTAMP_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: DISPLAY_TIME_ZONE,
  timeZoneName: "short",
});
const LOCAL_DATE_PARTS_FORMATTER = new Intl.DateTimeFormat("en-US", {
  timeZone: DISPLAY_TIME_ZONE,
  year: "numeric",
  month: "numeric",
  day: "numeric",
});
const WEEKDAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;
const WEEKDAY_INDEX: Record<string, number> = {
  sunday: 0,
  monday: 1,
  tuesday: 2,
  wednesday: 3,
  thursday: 4,
  friday: 5,
  saturday: 6,
};
const RELATIVE_DAY_PATTERN = /\b(today|tomorrow|yesterday)\b(?!')/gi;
const WEEKDAY_PATTERN =
  /\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/gi;
const EXPLICIT_DATE_SUFFIX_PATTERN =
  /^\s*(?:,?\s*(?:\d{1,2}\/\d{1,2}(?:\/\d{2,4})?|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+\d{1,2}(?:,\s*\d{4})?))/i;
const STAGE_HIGHLIGHT_PATTERN =
  /\b(?:Likely for a new project\.|Likely for a project currently underway\.|Project stage is unclear from the thread so far\.)/gi;
const EXPLICIT_WEEKDAY_DATE_PATTERN =
  /\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\/\d{1,2}\b/g;

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Unknown";
  }

  return TIMESTAMP_FORMATTER.format(new Date(value));
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

function getReferenceLocalDate(
  referenceTimestamp: string | null | undefined,
): Date | null {
  if (!referenceTimestamp) {
    return null;
  }

  const parts = LOCAL_DATE_PARTS_FORMATTER.formatToParts(new Date(referenceTimestamp));
  const year = Number(parts.find((part) => part.type === "year")?.value);
  const month = Number(parts.find((part) => part.type === "month")?.value);
  const day = Number(parts.find((part) => part.type === "day")?.value);

  if (!year || !month || !day) {
    return null;
  }

  return new Date(Date.UTC(year, month - 1, day, 12));
}

function shiftCalendarDate(value: Date, days: number) {
  const shifted = new Date(value.getTime());
  shifted.setUTCDate(shifted.getUTCDate() + days);
  return shifted;
}

function formatWeekdayMonthDay(value: Date) {
  return `${WEEKDAY_NAMES[value.getUTCDay()]} ${value.getUTCMonth() + 1}/${value.getUTCDate()}`;
}

function resolveWeekdayDate(
  weekdayText: string,
  referenceDate: Date,
  leadingContext: string,
) {
  const targetIndex = WEEKDAY_INDEX[weekdayText.toLowerCase()];
  const currentIndex = referenceDate.getUTCDay();
  const nextOffset = (targetIndex - currentIndex + 7) % 7;

  if (/\b(last|previous|earlier)\s*$/i.test(leadingContext)) {
    return shiftCalendarDate(referenceDate, nextOffset === 0 ? -7 : nextOffset - 7);
  }

  if (/\bnext\s*$/i.test(leadingContext)) {
    return shiftCalendarDate(referenceDate, nextOffset === 0 ? 7 : nextOffset);
  }

  return shiftCalendarDate(referenceDate, nextOffset);
}

function normalizeThreadDisplayText(
  text: string,
  referenceTimestamp: string | null | undefined,
) {
  let normalized = text.replace(/\u200b/g, " ").replace(/\s+/g, " ").trim();
  const referenceDate = getReferenceLocalDate(referenceTimestamp);

  if (!referenceDate) {
    return normalized;
  }

  normalized = normalized.replace(RELATIVE_DAY_PATTERN, (match) => {
    const offset =
      match.toLowerCase() === "yesterday"
        ? -1
        : match.toLowerCase() === "tomorrow"
          ? 1
          : 0;
    return formatWeekdayMonthDay(shiftCalendarDate(referenceDate, offset));
  });

  return normalized.replace(WEEKDAY_PATTERN, (match, _weekday, offset, fullText) => {
    const trailing = fullText.slice(offset + match.length);
    if (EXPLICIT_DATE_SUFFIX_PATTERN.test(trailing)) {
      return match;
    }

    const leading = fullText.slice(Math.max(0, offset - 24), offset);
    const resolved = resolveWeekdayDate(match, referenceDate, leading);
    const monthDay = `${resolved.getUTCMonth() + 1}/${resolved.getUTCDate()}`;
    return `${match} ${monthDay}`;
  });
}

function applyAutomaticSummaryHighlights(text: string) {
  if (text.includes("**")) {
    return text;
  }

  return text
    .replace(STAGE_HIGHLIGHT_PATTERN, "**$&**")
    .replace(EXPLICIT_WEEKDAY_DATE_PATTERN, "**$&**");
}

function renderBoldMarkers(text: string): ReactNode {
  if (!text.includes("**")) {
    return text;
  }

  return text.split("**").map((segment, index) =>
    index % 2 === 1 ? (
      <strong key={`segment-${index}`}>{segment}</strong>
    ) : (
      <Fragment key={`segment-${index}`}>{segment}</Fragment>
    ),
  );
}

function renderSummaryText(
  text: string,
  referenceTimestamp: string | null | undefined,
): ReactNode {
  const normalized = normalizeThreadDisplayText(text, referenceTimestamp);
  const highlighted = applyAutomaticSummaryHighlights(normalized);
  return renderBoldMarkers(highlighted);
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
        const focusTag =
          item.primaryEventTag && item.eventTags.includes(item.primaryEventTag)
            ? item.primaryEventTag
            : item.eventTags[0] ?? null;
        const visibleTags =
          dashboard === "needs_attention"
            ? focusTag
              ? [focusTag]
              : []
            : item.eventTags.slice(0, 2);
        const hiddenTags =
          dashboard === "needs_attention"
            ? item.eventTags.filter((tag) => tag !== focusTag)
            : item.eventTags.slice(2);
        const remainingTagCount = Math.max(item.eventTags.length - visibleTags.length, 0);
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
                  <span
                    className={`status-pill ${badgeTone(tag)}`}
                    key={tag}
                    title={
                      dashboard === "needs_attention" && hiddenTagsLabel
                        ? `Other signals: ${hiddenTagsLabel}`
                        : undefined
                    }
                  >
                    {EVENT_LABELS[tag] ?? tag}
                  </span>
                ))}
                {dashboard !== "needs_attention" && remainingTagCount > 0 ? (
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
              </div>
            </div>

            {item.cardHeader ? (
              <p className="thread-card__headline">
                {normalizeThreadDisplayText(
                  item.cardHeader,
                  item.latestCorrespondenceAt,
                )}
              </p>
            ) : null}

            <div className="thread-card__meta-grid">
              <span>Project: {item.projectNumber ?? "Unknown"}</span>
              <span>{item.messageCount} messages</span>
            </div>

            <p className="thread-card__snippet">
              {item.summary
                ? renderSummaryText(item.summary, item.latestCorrespondenceAt)
                : "No summary or snippet is stored yet for this thread."}
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
                    className={`thread-card__urgent-toggle ${
                      item.isUrgent
                        ? "thread-card__urgent-toggle--active"
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
