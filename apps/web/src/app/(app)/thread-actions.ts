"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

import { requireAnyRole, requireRole } from "@/lib/auth";
import { withClient } from "@/lib/server-db";

const REVIEW_STATES = new Set(["open", "handled", "disregard"]);
const PROMOTION_STATES = new Set(["promoted", "not_promoted"]);
const REPLY_STATES = new Set([
  "unanswered",
  "answered",
  "partial_answer",
  "answered_offline",
]);

function asString(value: FormDataEntryValue | null) {
  return typeof value === "string" ? value : null;
}

export async function updateThreadReviewStateAction(formData: FormData) {
  const actor = await requireAnyRole(["admin", "lead"]);

  const threadId = asString(formData.get("threadId"));
  const nextReviewState = asString(formData.get("reviewState"));
  const returnTo = asString(formData.get("returnTo")) ?? "/needs-attention";

  if (!threadId || !nextReviewState || !REVIEW_STATES.has(nextReviewState)) {
    throw new Error("Invalid thread state change request.");
  }

  await withClient(async (client) => {
    await client.query("begin");

    try {
      const { rows } = await client.query<{
        review_state: string;
        first_opened_at: string | null;
        promotion_state: string;
      }>(
        `
          select review_state, first_opened_at::text, promotion_state
          from public.thread_records
          where id = $1
          for update
        `,
        [threadId],
      );

      const currentRow = rows[0];
      if (!currentRow) {
        throw new Error("Thread not found.");
      }

      if (
        actor.role !== "admin" &&
        nextReviewState === "open" &&
        currentRow.promotion_state === "not_promoted" &&
        currentRow.first_opened_at === null
      ) {
        throw new Error("Only admins can promote a not-promoted thread into open.");
      }

      const { rows: updatedRows } = await client.query<{
        review_state: string;
        first_opened_at: string | null;
      }>(
        `
          update public.thread_records
          set review_state = $2,
              first_opened_at = case
                when $2 = 'open' and first_opened_at is null
                  then timezone('utc', now())
                else first_opened_at
              end,
              last_reviewed_at = timezone('utc', now()),
              state_last_changed_at = timezone('utc', now()),
              updated_at = timezone('utc', now())
          where id = $1
          returning review_state, first_opened_at::text
        `,
        [threadId, nextReviewState],
      );

      const updatedRow = updatedRows[0];
      if (!updatedRow) {
        throw new Error("Thread update failed.");
      }

      if (currentRow.review_state !== updatedRow.review_state) {
        await client.query(
          `
            insert into public.thread_state_history (
              thread_record_id,
              actor_type,
              actor_user_id,
              field_name,
              old_value,
              new_value,
              reason,
              source
            )
            values ($1, 'user', $2::uuid, 'review_state', $3::jsonb, $4::jsonb, $5, 'web_dashboard')
          `,
          [
            threadId,
            actor.id,
            JSON.stringify(currentRow.review_state),
            JSON.stringify(updatedRow.review_state),
            "Review state changed from dashboard.",
          ],
        );
      }

      if (currentRow.first_opened_at !== updatedRow.first_opened_at) {
        await client.query(
          `
            insert into public.thread_state_history (
              thread_record_id,
              actor_type,
              actor_user_id,
              field_name,
              old_value,
              new_value,
              reason,
              source
            )
            values ($1, 'user', $2::uuid, 'first_opened_at', $3::jsonb, $4::jsonb, $5, 'web_dashboard')
          `,
          [
            threadId,
            actor.id,
            JSON.stringify(currentRow.first_opened_at),
            JSON.stringify(updatedRow.first_opened_at),
            "Thread was opened from a dashboard action.",
          ],
        );
      }

      await client.query("commit");
    } catch (error) {
      await client.query("rollback");
      throw error;
    }
  });

  revalidatePath(returnTo);
  revalidatePath("/needs-attention");
  revalidatePath("/closed");
  revalidatePath("/not-promoted");
  revalidatePath("/admin");
  redirect(returnTo);
}

export async function overrideThreadClassificationAction(formData: FormData) {
  const actor = await requireRole("admin");

  const threadId = asString(formData.get("threadId"));
  const returnTo = asString(formData.get("returnTo")) ?? "/admin";
  const promotionState = asString(formData.get("promotionState"));
  const replyState = asString(formData.get("replyState"));
  const urgency = asString(formData.get("urgency"));
  const eventTagsRaw = asString(formData.get("eventTags")) ?? "";
  const cardHeader = asString(formData.get("cardHeader")) ?? "";
  const summary = asString(formData.get("summary")) ?? "";

  if (
    !threadId ||
    !promotionState ||
    !PROMOTION_STATES.has(promotionState) ||
    !replyState ||
    !REPLY_STATES.has(replyState) ||
    !["urgent", "not_urgent"].includes(urgency ?? "")
  ) {
    throw new Error("Invalid thread override request.");
  }

  const eventTags = eventTagsRaw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const primaryEventTag = eventTags[0] ?? null;
  const isUrgent = urgency === "urgent";

  await withClient(async (client) => {
    await client.query("begin");

    try {
      const { rows } = await client.query<{
        latest_classification_id: string | null;
        system_event_tags: string[];
        event_tags: string[];
        system_primary_event_tag: string | null;
        primary_event_tag: string | null;
        system_promotion_state: string;
        promotion_state: string;
        system_reply_state: string;
        reply_state: string;
        system_is_urgent: boolean;
        is_urgent: boolean;
        system_summary: string | null;
        summary: string | null;
        system_card_header: string | null;
        card_header: string | null;
      }>(
        `
          select
            latest_classification_id::text,
            system_event_tags,
            event_tags,
            system_primary_event_tag,
            primary_event_tag,
            system_promotion_state,
            promotion_state,
            system_reply_state,
            reply_state,
            system_is_urgent,
            is_urgent,
            system_card_header,
            card_header,
            system_summary,
            summary
          from public.thread_records
          where id = $1
          for update
        `,
        [threadId],
      );

      const currentRow = rows[0];
      if (!currentRow) {
        throw new Error("Thread not found.");
      }

      await client.query(
        `
          update public.thread_records
          set event_tags = $2::jsonb,
              primary_event_tag = $3,
              event_tags_overridden = true,
              promotion_state = $4,
              promotion_state_overridden = true,
              reply_state = $5,
              reply_state_overridden = true,
              is_urgent = $6,
              urgency_overridden = true,
              card_header = $7,
              card_header_overridden = true,
              summary = $8,
              summary_overridden = true,
              has_human_overrides = true,
              state_last_changed_at = timezone('utc', now()),
              updated_at = timezone('utc', now())
          where id = $1
        `,
        [
          threadId,
          JSON.stringify(eventTags),
          primaryEventTag,
          promotionState,
          replyState,
          isUrgent,
          cardHeader,
          summary,
        ],
      );

      const overrideRows = [
        {
          fieldName: "event_tags",
          systemValue: currentRow.system_event_tags,
          effectiveValue: eventTags,
        },
        {
          fieldName: "primary_event_tag",
          systemValue: currentRow.system_primary_event_tag,
          effectiveValue: primaryEventTag,
        },
        {
          fieldName: "promotion_state",
          systemValue: currentRow.system_promotion_state,
          effectiveValue: promotionState,
        },
        {
          fieldName: "reply_state",
          systemValue: currentRow.system_reply_state,
          effectiveValue: replyState,
        },
        {
          fieldName: "is_urgent",
          systemValue: currentRow.system_is_urgent,
          effectiveValue: isUrgent,
        },
        {
          fieldName: "summary",
          systemValue: currentRow.system_summary,
          effectiveValue: summary,
        },
        {
          fieldName: "card_header",
          systemValue: currentRow.system_card_header,
          effectiveValue: cardHeader,
        },
      ];

      for (const row of overrideRows) {
        await client.query(
          `
            insert into public.thread_state_history (
              thread_record_id,
              actor_type,
              actor_user_id,
              field_name,
              old_value,
              new_value,
              reason,
              source
            )
            values ($1, 'user', $2::uuid, $3, $4::jsonb, $5::jsonb, $6, 'admin_override')
          `,
          [
            threadId,
            actor.id,
            row.fieldName,
            JSON.stringify(row.systemValue),
            JSON.stringify(row.effectiveValue),
            "Admin override applied to effective thread state.",
          ],
        );

        await client.query(
          `
            insert into public.thread_override_feedback (
              thread_record_id,
              thread_classification_id,
              actor_user_id,
              field_name,
              system_value,
              effective_value,
              note
            )
            values ($1, $2, $3::uuid, $4, $5::jsonb, $6::jsonb, $7)
          `,
          [
            threadId,
            currentRow.latest_classification_id,
            actor.id,
            row.fieldName,
            JSON.stringify(row.systemValue),
            JSON.stringify(row.effectiveValue),
            "Manual override from the admin dashboard.",
          ],
        );
      }

      await client.query("commit");
    } catch (error) {
      await client.query("rollback");
      throw error;
    }
  });

  revalidatePath("/admin");
  redirect(returnTo);
}

export async function toggleThreadUrgencyAction(formData: FormData) {
  const actor = await requireAnyRole(["admin", "lead"]);

  const threadId = asString(formData.get("threadId"));
  const returnTo = asString(formData.get("returnTo")) ?? "/needs-attention";

  if (!threadId) {
    throw new Error("Missing thread for urgency toggle.");
  }

  await withClient(async (client) => {
    await client.query("begin");

    try {
      const { rows } = await client.query<{
        latest_classification_id: string | null;
        system_is_urgent: boolean;
        is_urgent: boolean;
      }>(
        `
          select
            latest_classification_id::text,
            system_is_urgent,
            is_urgent
          from public.thread_records
          where id = $1
          for update
        `,
        [threadId],
      );

      const currentRow = rows[0];
      if (!currentRow) {
        throw new Error("Thread not found.");
      }

      const nextUrgency = !currentRow.is_urgent;

      await client.query(
        `
          update public.thread_records
          set is_urgent = $2,
              urgency_overridden = true,
              has_human_overrides = true,
              state_last_changed_at = timezone('utc', now()),
              updated_at = timezone('utc', now())
          where id = $1
        `,
        [threadId, nextUrgency],
      );

      await client.query(
        `
          insert into public.thread_state_history (
            thread_record_id,
            actor_type,
            actor_user_id,
            field_name,
            old_value,
            new_value,
            reason,
            source
          )
          values ($1, 'user', $2::uuid, 'is_urgent', $3::jsonb, $4::jsonb, $5, 'dashboard_urgency_toggle')
        `,
        [
          threadId,
          actor.id,
          JSON.stringify(currentRow.is_urgent),
          JSON.stringify(nextUrgency),
          "Urgency toggled from thread card.",
        ],
      );

      await client.query(
        `
          insert into public.thread_override_feedback (
            thread_record_id,
            thread_classification_id,
            actor_user_id,
            field_name,
            system_value,
            effective_value,
            note
          )
          values ($1, $2, $3::uuid, 'is_urgent', $4::jsonb, $5::jsonb, $6)
        `,
        [
          threadId,
          currentRow.latest_classification_id,
          actor.id,
          JSON.stringify(currentRow.system_is_urgent),
          JSON.stringify(nextUrgency),
          "Urgency manually toggled from a dashboard card.",
        ],
      );

      await client.query("commit");
    } catch (error) {
      await client.query("rollback");
      throw error;
    }
  });

  revalidatePath(returnTo);
  revalidatePath("/needs-attention");
  revalidatePath("/closed");
  revalidatePath("/not-promoted");
  revalidatePath("/admin");
  redirect(returnTo);
}
