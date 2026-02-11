/**
 * Services Layer - Unified Export
 *
 * Exports all domain-specific service modules.
 * Each service contains typed API functions that communicate with the backend.
 *
 * Usage:
 *   import { octopusosService, memoryosService } from '@services';
 *   const projects = await octopusosService.listProjectsApiProjectsGet();
 *
 * Organization:
 * - octopusos.service.ts: Projects, Tasks, Repos, Sessions, Task Templates, Dependencies, Events, Audit
 * - memoryos.service.ts: Memory search, timeline, proposals
 * - brainos.service.ts: Knowledge, decisions, review queue, governance, intent, metrics
 * - skillos.service.ts: Skills, extensions, templates, execution, governance
 * - networkos.service.ts: Capabilities, governance dashboard, guardians, execution policies, evidence
 * - communicationos.service.ts: Channels, marketplace, sessions, voice, MCP
 * - appos.service.ts: Application management, lifecycle, status
 * - system.service.ts: Config, providers, models, health, secrets, auth, history, logs, share, preview, snippets, budget, mode, demo, metrics
 */

// OctopusOS - generated default
export { octopusosServiceGen as octopusosService } from './octopusos.service.gen';
export type * from './octopusos.service';

// MemoryOS - generated default
export { memoryosServiceGen as memoryosService } from './memoryos.service.gen';
export type * from './memoryos.service';

// BrainOS - generated default
export { brainosServiceGen as brainosService } from './brainos.service.gen';
export type * from './brainos.service';

// SkillOS - generated default
export { skillosServiceGen as skillosService } from './skillos.service.gen';
export type * from './skillos.service';

// NetworkOS - generated default
export { networkosServiceGen as networkosService } from './networkos.service.gen';
export type * from './networkos.service';

// CommunicationOS - generated default
export { communicationosServiceGen as communicationosService } from './communicationos.service.gen';
export type * from './communicationos.service';

// AppOS - generated default
export { apposServiceGen as apposService } from './appos.service.gen';
export type * from './appos.service';

// System - generated default
export { systemServiceGen as systemService } from './system.service.gen';
export type * from './system.service';

// Frontdesk - Global frontdesk chat
export { frontdeskService } from './frontdesk.service';
export type * from './frontdesk.service';

// Inbox - Attention cards (Phase 2)
export { inboxService } from './inbox.service';
export type * from './inbox.service';

// Work items + exec tasks (Phase 4)
export { workItemsService } from './work_items.service';
export type * from './work_items.service';
export { execTasksService } from './exec_tasks.service';
export type * from './exec_tasks.service';

// ChangeLog (MD-backed)
export { changelogService } from './changelog.service';
export type * from './changelog.service';

// Dispatch - Proposal hub
export { dispatchService } from './dispatch.service';
export type * from './dispatch.service';

// Email channel (backed by MCP providers/instances)
export { emailService } from './email.service';
export type * from './email.service';
