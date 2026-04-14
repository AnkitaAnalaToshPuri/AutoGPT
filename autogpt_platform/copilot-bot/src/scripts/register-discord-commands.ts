/**
 * Register Discord slash commands with the bot's application.
 *
 * Run once after adding/changing commands:
 *   npx tsx src/scripts/register-discord-commands.ts
 *
 * Requires DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID in .env.
 * Global commands take up to 1 hour to propagate. For local testing,
 * pass DISCORD_DEV_GUILD_ID to register against a single guild instantly.
 */

import "dotenv/config";

interface SlashCommand {
  name: string;
  description: string;
}

const COMMANDS: SlashCommand[] = [
  {
    name: "setup",
    description:
      "Link this server to an AutoGPT account so everyone here can use AutoPilot.",
  },
  {
    name: "unlink",
    description: "Manage linked servers from your AutoGPT settings.",
  },
  {
    name: "help",
    description: "Show AutoPilot bot usage info.",
  },
];

async function main() {
  const token = process.env.DISCORD_BOT_TOKEN;
  const appId = process.env.DISCORD_APPLICATION_ID;
  const devGuildId = process.env.DISCORD_DEV_GUILD_ID;

  if (!token || !appId) {
    console.error(
      "Missing DISCORD_BOT_TOKEN or DISCORD_APPLICATION_ID in environment.",
    );
    process.exit(1);
  }

  const url = devGuildId
    ? `https://discord.com/api/v10/applications/${appId}/guilds/${devGuildId}/commands`
    : `https://discord.com/api/v10/applications/${appId}/commands`;

  console.log(
    `Registering ${COMMANDS.length} command(s) ${devGuildId ? `to guild ${devGuildId}` : "globally"}...`,
  );

  const res = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bot ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(COMMANDS),
  });

  if (!res.ok) {
    console.error(`Failed: ${res.status} ${res.statusText}`);
    console.error(await res.text());
    process.exit(1);
  }

  const registered = (await res.json()) as Array<{ name: string; id: string }>;
  console.log("Registered:");
  for (const cmd of registered) {
    console.log(`  /${cmd.name} (id: ${cmd.id})`);
  }

  if (!devGuildId) {
    console.log(
      "\nGlobal commands can take up to 1 hour to appear. For instant testing,",
    );
    console.log("set DISCORD_DEV_GUILD_ID=<guild_id> and re-run.");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
