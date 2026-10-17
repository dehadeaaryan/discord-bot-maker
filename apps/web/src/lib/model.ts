import type { BotDefinition, Trigger, Reply, Embed, Condition, Edge, Position } from './definition.generated';
export type Block = (Trigger & { kind: 'trigger' }) | (Reply & { kind: 'reply' }) | (Embed & { kind: 'embed' }) | (Condition & { kind: 'condition' });
export type Definition = Omit<BotDefinition, 'nodes' | 'edges' | 'layout' | 'name' | 'prefix'> & {
  name: string; prefix: string; nodes: Block[]; edges: Edge[];
  layout: { positions: Record<string, Position> };
};
export type Project = { id: string; name: string; version: number; definition: Definition; has_token: boolean; application_id: string | null; guild_id: string | null; published_revision: string | null; desired_state: string; observed_state: string };
export type PreviewResult = { messages: { kind: string; content?: string; title?: string; description?: string; color?: string; image_url?: string; ephemeral: boolean }[]; trace: { id: string; kind: string; result?: string }[] };
export const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));
