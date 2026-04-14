/**
 * Discord interaction API types — just what we use.
 * Full reference: https://discord.com/developers/docs/interactions/receiving-and-responding
 */

export const InteractionType = {
  Ping: 1,
  ApplicationCommand: 2,
  MessageComponent: 3,
  Autocomplete: 4,
  ModalSubmit: 5,
} as const;

export const ResponseType = {
  Pong: 1,
  ChannelMessageWithSource: 4,
  DeferredChannelMessageWithSource: 5,
  DeferredUpdateMessage: 6,
  UpdateMessage: 7,
  Modal: 9,
} as const;

export const MessageFlag = {
  Ephemeral: 1 << 6,
} as const;

export const ComponentType = {
  ActionRow: 1,
  Button: 2,
  StringSelect: 3,
  TextInput: 4,
} as const;

export const ButtonStyle = {
  Primary: 1,
  Secondary: 2,
  Success: 3,
  Danger: 4,
  Link: 5,
} as const;

export interface DiscordUser {
  id: string;
  username: string;
  global_name?: string | null;
}

export interface DiscordInteraction {
  id: string;
  token: string;
  type: number;
  guild_id?: string;
  channel_id?: string;
  application_id: string;
  data?: {
    name?: string;
    custom_id?: string;
    options?: Array<{ name: string; value: unknown }>;
    components?: Array<{
      type: number;
      components?: Array<{ type: number; custom_id: string; value: string }>;
    }>;
  };
  member?: { user: DiscordUser };
  user?: DiscordUser;
  message?: { id: string; content: string };
}

export interface Component {
  type: number;
  style?: number;
  label?: string;
  custom_id?: string;
  url?: string;
  disabled?: boolean;
  emoji?: { name: string };
  components?: Component[];
}
