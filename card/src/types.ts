export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, any>;
  last_changed: string;
  last_updated: string;
}

export interface HassEntityRegistryEntry {
  entity_id: string;
  device_id?: string | null;
  platform: string;
  translation_key?: string | null;
}

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  entities: Record<string, HassEntityRegistryEntry>;
  config: { time_zone: string };
  locale: { language: string; time_format?: string };
  callService: (domain: string, service: string, data?: Record<string, unknown>) => Promise<unknown>;
  callWS: <T = any>(msg: Record<string, unknown>) => Promise<T>;
}

export interface ZoneMinderCardConfig {
  type: string;
  /** Cameras to show. Defaults to every ZoneMinder camera. */
  entities?: Array<string | { entity: string; name?: string }>;
  /** Fixed column count. Without it the grid fits as many as the width allows. */
  columns?: number;
  /** How much history the strip covers. */
  hours?: number;
  /** Show the PTZ pad on cameras that can move. */
  ptz?: boolean;
}

/** One ZoneMinder event, as the integration's `zoneminder/events` command returns it. */
export interface ZmEvent {
  id: number;
  start: string;
  end: string | null;
  length: number;
  cause: string;
  notes: string | null;
  alarm_frames: number;
  max_score: number;
  in_progress: boolean;
  thumbnail: string | null;
  video: string | null;
}

export interface ZmEventWindow {
  start: string;
  end: string;
  events: ZmEvent[];
}
