import type { BotDefinition, Trigger, Reply, Embed, Condition, InteractiveMessage, Form, Action, Edge, Position } from './definition.generated';
export type Block = (Trigger & { kind: 'trigger' }) | (Reply & { kind: 'reply' }) | (Embed & { kind: 'embed' }) | (Condition & { kind: 'condition' }) | (InteractiveMessage & { kind: 'message' }) | (Form & { kind: 'form' }) | (Action & { kind: 'action' });
export type Definition = Omit<BotDefinition, 'nodes' | 'edges' | 'layout' | 'name' | 'prefix'> & {
  name: string; prefix: string; nodes: Block[]; edges: Edge[];
  layout: { positions: Record<string, Position> };
};
export type Project = { id: string; name: string; version: number; definition: Definition; has_token: boolean; application_id: string | null; guild_id: string | null; published_revision: string | null; desired_state: string; observed_state: string };
export type PreviewMessage = { kind: string; node_id?: string; content?: string; title?: string; description?: string; color?: string; image_url?: string; footer?: string; fields?: {name:string; value:string; inline:boolean}[]; ephemeral: boolean; buttons?: {label:string; url?:string|null}[]; selects?: {placeholder:string; options:string[]}[]; inputs?: {name:string; label:string; required:boolean; max_length:number; paragraph:boolean}[]; attachments?: {filename:string; content:string}[]; operation?:string };
export type PreviewState = {values: Record<string, Record<string, unknown>>; jobs: Record<string, Record<string, unknown>>};
export type PreviewResult = { messages: PreviewMessage[]; trace: { id: string; kind: string; result?: string }[]; state: PreviewState };
export const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));
