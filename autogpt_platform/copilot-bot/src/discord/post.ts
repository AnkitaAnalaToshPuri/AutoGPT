/**
 * Direct Discord REST API posting — used when the Chat SDK's Card/Actions
 * abstraction wraps our content in an embed with duplicate fallback text.
 *
 * Posts `content` + `components` inline so the text renders as a normal
 * message body with buttons underneath, no embed clutter.
 */

import type { Component } from "./types.js";

const DISCORD_API = "https://discord.com/api/v10";

/**
 * Extract the Discord channel ID from a thread ID.
 * Thread ID format: "discord:{guildId}:{channelId}[:{threadId}]"
 * We post to the deepest segment available — so in a thread we post to the
 * thread, not the parent channel.
 */
export function discordPostTarget(threadId: string): string {
  const parts = threadId.split(":");
  // Format: discord:guild:channel[:thread]
  return parts[3] ?? parts[2] ?? parts[1] ?? parts[0];
}

/**
 * Post a message to a Discord channel with content + interactive components.
 * Returns the message ID.
 */
export async function postDiscordMessage(
  channelId: string,
  content: string,
  components: Component[],
): Promise<string | null> {
  const token = process.env.DISCORD_BOT_TOKEN;
  if (!token) {
    throw new Error("DISCORD_BOT_TOKEN not set");
  }

  const res = await fetch(`${DISCORD_API}/channels/${channelId}/messages`, {
    method: "POST",
    headers: {
      Authorization: `Bot ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content, components }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Discord post failed (${res.status}): ${text}`);
  }

  const data = (await res.json()) as { id: string };
  return data.id;
}
