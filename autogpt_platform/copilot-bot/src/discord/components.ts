/**
 * Helpers for building Discord message components (buttons, selects, rows).
 *
 * `custom_id` is the key we match in the component handler registry, so use
 * deterministic prefixes like "regenerate" or "end-session:{sessionId}".
 * Max 100 chars for custom_id, max 5 components per action row, max 5 rows.
 */

import {
  ButtonStyle,
  ComponentType,
  type Component,
} from "./types.js";

export interface ButtonOpts {
  style?: keyof typeof ButtonStyle;
  emoji?: string;
  disabled?: boolean;
}

/** Build an interactive button (registers against custom_id). */
export function button(
  customId: string,
  label: string,
  opts: ButtonOpts = {},
): Component {
  if (customId.length > 100) {
    throw new Error(`custom_id too long (${customId.length} > 100): ${customId}`);
  }
  return {
    type: ComponentType.Button,
    style: ButtonStyle[opts.style ?? "Secondary"],
    label,
    custom_id: customId,
    emoji: opts.emoji ? { name: opts.emoji } : undefined,
    disabled: opts.disabled,
  };
}

/** Build a link button (no handler — just opens a URL). */
export function linkButton(url: string, label: string, emoji?: string): Component {
  return {
    type: ComponentType.Button,
    style: ButtonStyle.Link,
    label,
    url,
    emoji: emoji ? { name: emoji } : undefined,
  };
}

/** Wrap components in an action row. Max 5 per row. */
export function row(...components: Component[]): Component {
  if (components.length > 5) {
    throw new Error(`Too many components in row (${components.length} > 5)`);
  }
  return { type: ComponentType.ActionRow, components };
}
