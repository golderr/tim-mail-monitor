import { overrideThreadClassificationAction } from "@/app/(app)/thread-actions";
import type { DashboardThread } from "@/lib/dashboard-data";

export function AdminThreadOverrideForm({
  item,
  returnTo,
}: Readonly<{
  item: DashboardThread;
  returnTo: string;
}>) {
  return (
    <details className="override-panel">
      <summary>Override classifier output</summary>

      <form action={overrideThreadClassificationAction} className="override-form">
        <input type="hidden" name="threadId" value={item.id} />
        <input type="hidden" name="returnTo" value={returnTo} />

        <label className="field">
          <span>Event Tags</span>
          <input
            defaultValue={item.eventTags.join(", ")}
            name="eventTags"
            placeholder="deadline, scope_change"
          />
        </label>

        <label className="field">
          <span>Card Header</span>
          <input
            defaultValue={item.cardHeader ?? ""}
            name="cardHeader"
            placeholder="Estimated meeting date: Apr 20"
          />
        </label>

        <label className="field">
          <span>Promotion</span>
          <select defaultValue={item.promotionState} name="promotionState">
            <option value="promoted">Promoted</option>
            <option value="not_promoted">Not Promoted</option>
          </select>
        </label>

        <label className="field">
          <span>Reply State</span>
          <select defaultValue={item.replyState} name="replyState">
            <option value="unanswered">Unanswered</option>
            <option value="answered">Answered</option>
            <option value="partial_answer">Partial Answer</option>
            <option value="answered_offline">Answered Offline</option>
          </select>
        </label>

        <label className="field">
          <span>Urgency</span>
          <select
            defaultValue={item.isUrgent ? "urgent" : "not_urgent"}
            name="urgency"
          >
            <option value="urgent">Urgent</option>
            <option value="not_urgent">Not Urgent</option>
          </select>
        </label>

        <label className="field">
          <span>Summary</span>
          <textarea
            defaultValue={item.summary ?? ""}
            name="summary"
            rows={3}
          />
        </label>

        <button className="primary-button" type="submit">
          Save Override
        </button>
      </form>
    </details>
  );
}
