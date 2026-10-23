import { LovelaceCard, LovelaceCardConfig, LovelaceCardEditor } from 'custom-card-helpers';

// CSS module declaration for rollup-plugin-postcss
declare module '*.css' {
  const content: string;
  export default content;
}

declare global {
  interface HTMLElementTagNameMap {
    'zoneminder-card': ZoneMinerCard;
    'zoneminder-card-editor': ZoneMinerCardEditor;
    'webrtc-player': WebRTCPlayer;
  }
}

export interface ZoneMinerCardConfig extends LovelaceCardConfig {
  type: string;
  title?: string;
  zoneminder_go2rtc_url?: string; // Auto-detected from integration if not provided
  monitors: MonitorConfig[];
  columns?: number;               // Number of grid columns (default: 4, even number recommended)
  aspect_ratio?: string;
  streaming_mode?: StreamingMode;
  show_motion_indicator?: boolean;
  show_controls?: boolean;
  show_timeline?: boolean;
  refresh_interval?: number;
  click_action?: 'fullscreen' | 'events' | 'none';
}

export interface MonitorConfig {
  entity: string; // camera.front_door
  stream_id?: string; // Monitor ID for go2rtc (auto-detected from entity attributes if not provided)
  name?: string; // Override monitor name
  columns?: number; // How many grid columns this monitor should span (default: 1)
  rows?: number; // How many grid rows this monitor should span (default: 1)
}

export type StreamingMode = 'webrtc' | 'mse' | 'hls' | 'mjpeg';

export interface HomeAssistant {
  states: { [entity_id: string]: HassEntity };
  callService: (domain: string, service: string, data?: any) => Promise<void>;
  callWS: (msg: any) => Promise<any>;
  // Add more HA types as needed
}

export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: { [key: string]: any };
  last_changed: string;
  last_updated: string;
  context: {
    id: string;
    parent_id: string | null;
    user_id: string | null;
  };
}

export interface WebRTCMessage {
  type: 'webrtc/offer' | 'webrtc/answer' | 'webrtc/candidate';
  value: string;
}

export interface ZoneMinerCard extends LovelaceCard {
  setConfig(config: ZoneMinerCardConfig): void;
}

export interface ZoneMinerCardEditor extends LovelaceCardEditor {
  setConfig(config: ZoneMinerCardConfig): void;
}

export interface WebRTCPlayer extends HTMLElement {
  go2rtcUrl: string;
  streamId: string;
  mode: StreamingMode;
  connect(): Promise<void>;
  disconnect(): void;
}
