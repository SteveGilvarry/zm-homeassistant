import { LitElement, html, css, nothing, PropertyValues, svg } from "lit";
import { property, state, query } from "lit/decorators.js";
import type {
  HomeAssistant,
  HassEntity,
  ZoneMinderCardConfig,
  ZmEvent,
  ZmEventWindow,
} from "./types";

declare global {
  interface Window {
    customCards?: Array<Record<string, unknown>>;
    loadCardHelpers?: () => Promise<any>;
  }
}

const DOMAIN = "zoneminder";
const DEFAULT_HOURS = 24;
const REFRESH_MS = 60_000;
/** Clips closer together than this play on as one recording. */
const JOIN_GAP_MS = 5_000;
const SPEEDS = [1, 4, 16];

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

let fontRequested = false;
/** Barlow Semi Condensed is in the brief; the system face stands in if it can't load. */
function requestFont(): void {
  if (fontRequested) return;
  fontRequested = true;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href =
    "https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;500;600&display=swap";
  document.head.appendChild(link);
}

let cameraStreamLoad: Promise<void> | undefined;
/**
 * `ha-camera-stream` is part of Home Assistant's frontend but loads lazily.
 * Building a picture-entity card pulls it in without us bundling a copy.
 */
function loadCameraStream(entity: string): Promise<void> {
  if (customElements.get("ha-camera-stream")) return Promise.resolve();
  cameraStreamLoad ??= (async () => {
    const helpers = await window.loadCardHelpers?.();
    const card = await helpers?.createCardElement({
      type: "picture-entity",
      entity,
      camera_view: "live",
    });
    card?.remove?.();
    await customElements.whenDefined("ha-camera-stream");
  })();
  return cameraStreamLoad;
}

/** Whether a live player (in any shadow root below `root`) has frames on screen. */
function playingVideo(root: Element): boolean {
  const stack: Array<Element | ShadowRoot> = [root];
  while (stack.length) {
    const node = stack.pop()!;
    if (
      node instanceof HTMLVideoElement &&
      node.readyState >= 2 &&
      node.videoWidth > 0
    ) {
      return true;
    }
    if (node instanceof Element && node.shadowRoot) stack.push(node.shadowRoot);
    stack.push(...Array.from(node.children));
  }
  return false;
}

function zoneminderCameras(hass: HomeAssistant): string[] {
  return Object.values(hass.entities ?? {})
    .filter((e) => e.platform === DOMAIN && e.entity_id.startsWith("camera."))
    .map((e) => e.entity_id)
    .filter((id) => hass.states[id])
    .sort((a, b) => name(hass.states[a]).localeCompare(name(hass.states[b])));
}

function name(state: HassEntity | undefined): string {
  return state?.attributes.friendly_name ?? state?.entity_id ?? "";
}

function motionEntity(
  hass: HomeAssistant,
  cameraId: string,
): string | undefined {
  const device = hass.entities?.[cameraId]?.device_id;
  if (!device) return undefined;
  return Object.values(hass.entities).find(
    (e) =>
      e.device_id === device &&
      e.platform === DOMAIN &&
      e.entity_id.startsWith("binary_sensor.") &&
      e.translation_key === "motion",
  )?.entity_id;
}

interface Clip {
  event: ZmEvent;
  start: number;
  end: number;
}

interface Band {
  start: number;
  end: number;
}

function toClips(events: ZmEvent[], now: number): Clip[] {
  return events.map((event) => {
    const start = Date.parse(event.start);
    const end = event.end
      ? Date.parse(event.end)
      : event.in_progress
        ? now
        : start + event.length * 1000;
    return { event, start, end: Math.max(end, start + 1000) };
  });
}

function toBands(clips: Clip[]): Band[] {
  const bands: Band[] = [];
  for (const clip of clips) {
    const last = bands[bands.length - 1];
    if (last && clip.start - last.end <= JOIN_GAP_MS) {
      last.end = Math.max(last.end, clip.end);
    } else {
      bands.push({ start: clip.start, end: clip.end });
    }
  }
  return bands;
}

class Clock {
  private time: Intl.DateTimeFormat;
  private hour: Intl.DateTimeFormat;
  private hourNumber: Intl.DateTimeFormat;
  private day: Intl.DateTimeFormat;
  private dayKey: Intl.DateTimeFormat;

  constructor(hass: HomeAssistant) {
    const timeZone = hass.config?.time_zone;
    const locale = hass.locale?.language ?? navigator.language;
    const hour12 =
      hass.locale?.time_format === "12"
        ? true
        : hass.locale?.time_format === "24"
          ? false
          : undefined;
    this.time = new Intl.DateTimeFormat(locale, {
      timeZone,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12,
    });
    this.hour = new Intl.DateTimeFormat(locale, {
      timeZone,
      hour: "numeric",
      hour12,
    });
    this.hourNumber = new Intl.DateTimeFormat("en-GB", {
      timeZone,
      hour: "2-digit",
      hour12: false,
    });
    this.day = new Intl.DateTimeFormat(locale, { timeZone, weekday: "short" });
    this.dayKey = new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  }

  formatTime(t: number): string {
    return this.time.format(t);
  }

  /** Time with the weekday when it isn't today. */
  formatMoment(t: number): string {
    const sameDay = this.dayKey.format(t) === this.dayKey.format(Date.now());
    return sameDay
      ? this.formatTime(t)
      : `${this.day.format(t)} ${this.formatTime(t)}`;
  }

  /** Hour marks every six local hours; midnight is named by its day. */
  ticks(
    start: number,
    end: number,
  ): Array<{ t: number; label: string; midnight: boolean }> {
    const out: Array<{ t: number; label: string; midnight: boolean }> = [];
    const hourMs = 3_600_000;
    for (let t = Math.ceil(start / hourMs) * hourMs; t <= end; t += hourMs) {
      const h = Number(this.hourNumber.format(t)) % 24;
      if (h % 6 !== 0) continue;
      out.push({
        t,
        label: h === 0 ? this.day.format(t) : this.hour.format(t),
        midnight: h === 0,
      });
    }
    return out;
  }
}

// ---------------------------------------------------------------------------
// Visual tokens
// ---------------------------------------------------------------------------

const tokens = css`
  :host {
    --zm-asphalt: #182026;
    --zm-kerb: #232c33;
    --zm-concrete: #7e8890;
    --zm-fog: #e3e7e9;
    --zm-tape: #3e6e8c;
    --zm-sodium: #f0a23b;
    --zm-font:
      "Barlow Semi Condensed", "Roboto Condensed", system-ui, sans-serif;
  }
`;

// ---------------------------------------------------------------------------
// One camera
// ---------------------------------------------------------------------------

export class ZmCameraTile extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property() entity = "";
  @property() label?: string;
  @property({ type: Number }) hours = DEFAULT_HOURS;
  @property({ type: Boolean }) ptz = true;

  @state() private visible = false;
  @state() private streamReady = false;
  /** True once the live player is showing real frames. */
  @state() private liveShowing = false;
  @state() private window?: ZmEventWindow;
  @state() private error?: string;
  /** Set while a recording plays instead of the live view. */
  @state() private playing?: { clip: Clip; at: number };
  @state() private paused = false;
  @state() private speed = 1;
  @state() private hover?: { t: number; x: number; clip?: Clip };
  /** Keyboard cursor on the strip, while it has focus. */
  @state() private cursor?: number;

  @query("video.playback") private recordingVideo?: HTMLVideoElement;

  private observer?: IntersectionObserver;
  private refreshTimer?: number;
  private lastMotion?: string;
  private seekOnLoad?: number;
  private livePoll?: number;

  connectedCallback(): void {
    super.connectedCallback();
    this.observer = new IntersectionObserver(
      ([entry]) => {
        this.visible = entry.isIntersecting;
        if (this.visible && !this.window) this.load();
      },
      { rootMargin: "200px" },
    );
    this.observer.observe(this);
    this.refreshTimer = window.setInterval(
      () => this.visible && this.load(),
      REFRESH_MS,
    );
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.observer?.disconnect();
    window.clearInterval(this.refreshTimer);
    window.clearInterval(this.livePoll);
  }

  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass) {
      // A motion event that just ended is a new recording worth showing.
      const motion = this.motionState;
      if (this.lastMotion === "on" && motion === "off") this.load();
      this.lastMotion = motion;
    }
    if (changed.has("visible") && this.visible && !this.streamReady) {
      loadCameraStream(this.entity).then(() => (this.streamReady = true));
    }
  }

  protected updated(): void {
    const stream = this.renderRoot.querySelector("ha-camera-stream");
    if (!stream) {
      this.liveShowing = false;
      window.clearInterval(this.livePoll);
      this.livePoll = undefined;
      return;
    }
    if (this.liveShowing || this.livePoll) return;
    // Until its video plays, the player shows ZoneMinder's still, which is
    // already upright and would come out sideways in the turned layer. The
    // still underneath covers that gap instead.
    this.livePoll = window.setInterval(() => {
      if (playingVideo(stream)) {
        this.liveShowing = true;
        window.clearInterval(this.livePoll);
        this.livePoll = undefined;
      }
    }, 300);
  }

  private get stateObj(): HassEntity | undefined {
    return this.hass?.states[this.entity];
  }

  private get motionState(): string | undefined {
    const id = motionEntity(this.hass, this.entity);
    return id ? this.hass.states[id]?.state : undefined;
  }

  private get clock(): Clock {
    return new Clock(this.hass);
  }

  private async load(): Promise<void> {
    try {
      this.window = await this.hass.callWS<ZmEventWindow>({
        type: "zoneminder/events",
        entity_id: this.entity,
        hours: this.hours,
      });
      this.error = undefined;
    } catch (err: any) {
      this.error = err?.message ?? String(err);
    }
  }

  private get span(): { start: number; end: number } {
    const end = Date.now();
    return { start: end - this.hours * 3_600_000, end };
  }

  private get clips(): Clip[] {
    return this.window ? toClips(this.window.events, Date.now()) : [];
  }

  private clipAt(t: number): Clip | undefined {
    return this.clips.find((c) => c.start <= t && t < c.end && c.event.video);
  }

  /** The clip covering `t`, or failing that the next one after it. */
  private clipFrom(t: number): Clip | undefined {
    return (
      this.clipAt(t) ?? this.clips.find((c) => c.start > t && c.event.video)
    );
  }

  // -- Playback ------------------------------------------------------------

  private play(t: number): void {
    const clip = this.clipFrom(t);
    if (!clip) return;
    const at = Math.max(t, clip.start);
    const sameClip = this.playing?.clip.event.id === clip.event.id;
    this.playing = { clip, at };
    this.paused = false;
    const offset = (at - clip.start) / 1000;
    if (sameClip && this.recordingVideo) {
      this.recordingVideo.currentTime = offset;
      this.recordingVideo.play();
    } else {
      this.seekOnLoad = offset;
    }
  }

  private backToLive(): void {
    this.playing = undefined;
    this.paused = false;
  }

  private onLoaded(ev: Event): void {
    const video = ev.target as HTMLVideoElement;
    if (this.seekOnLoad !== undefined) video.currentTime = this.seekOnLoad;
    this.seekOnLoad = undefined;
    video.playbackRate = this.speed;
    video.play().catch(() => (this.paused = true));
  }

  private onTimeUpdate(ev: Event): void {
    if (!this.playing) return;
    const video = ev.target as HTMLVideoElement;
    this.playing = {
      ...this.playing,
      at: this.playing.clip.start + video.currentTime * 1000,
    };
  }

  /** Continuous recording is cut into clips; play straight on into the next. */
  private onEnded(): void {
    if (!this.playing) return;
    const next = this.clips.find(
      (c) =>
        c.start >= this.playing!.clip.end - JOIN_GAP_MS &&
        c.event.id !== this.playing!.clip.event.id &&
        c.event.video,
    );
    if (next && next.start - this.playing.clip.end <= JOIN_GAP_MS) {
      this.playing = { clip: next, at: next.start };
      this.seekOnLoad = 0;
    } else {
      this.paused = true;
    }
  }

  private togglePause(): void {
    const video = this.recordingVideo;
    if (!video) return;
    if (video.paused) {
      video.play();
      this.paused = false;
    } else {
      video.pause();
      this.paused = true;
    }
  }

  private cycleSpeed(): void {
    this.speed = SPEEDS[(SPEEDS.indexOf(this.speed) + 1) % SPEEDS.length];
    if (this.recordingVideo) this.recordingVideo.playbackRate = this.speed;
  }

  // -- Strip interaction ---------------------------------------------------

  private timeAt(ev: PointerEvent): { t: number; x: number } {
    const rect = (ev.currentTarget as HTMLElement).getBoundingClientRect();
    const x = Math.min(Math.max(ev.clientX - rect.left, 0), rect.width);
    const { start, end } = this.span;
    return { t: start + (x / rect.width) * (end - start), x };
  }

  private onStripMove(ev: PointerEvent): void {
    const { t, x } = this.timeAt(ev);
    this.hover = { t, x, clip: this.clipAt(t) };
  }

  private onStripClick(ev: PointerEvent): void {
    this.play(this.timeAt(ev).t);
  }

  private onStripKey(ev: KeyboardEvent): void {
    const { start, end } = this.span;
    const step = (ev.shiftKey ? 10 : 1) * 60_000;
    const from = this.cursor ?? this.playing?.at ?? end;
    let next: number | undefined;
    switch (ev.key) {
      case "ArrowLeft":
        next = from - step;
        break;
      case "ArrowRight":
        next = from + step;
        break;
      case "Home":
        next = start;
        break;
      case "End":
        next = end;
        break;
      case "Enter":
      case " ":
        ev.preventDefault();
        this.play(from);
        return;
      case "Escape":
        this.backToLive();
        return;
      default:
        return;
    }
    ev.preventDefault();
    this.cursor = Math.min(Math.max(next, start), end);
  }

  // -- PTZ -----------------------------------------------------------------

  private ptzCommand(command: string): void {
    this.hass.callService(DOMAIN, "ptz", { entity_id: this.entity, command });
  }

  private ptzButton(command: string, icon: string, label: string) {
    const start = (ev: Event) => {
      ev.preventDefault();
      this.ptzCommand(command);
    };
    const stop = () => command !== "home" && this.ptzCommand("stop");
    return html`<button
      class="ptz-${command}"
      aria-label=${label}
      @pointerdown=${start}
      @pointerup=${stop}
      @pointerleave=${(ev: PointerEvent) => ev.buttons && stop()}
      @keydown=${(ev: KeyboardEvent) =>
        (ev.key === "Enter" || ev.key === " ") && !ev.repeat && start(ev)}
      @keyup=${(ev: KeyboardEvent) =>
        (ev.key === "Enter" || ev.key === " ") && stop()}
    >
      <ha-icon icon=${icon}></ha-icon>
    </button>`;
  }

  private moreInfo(): void {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId: this.entity },
        bubbles: true,
        composed: true,
      }),
    );
  }

  // -- Rendering -----------------------------------------------------------

  protected render() {
    const stateObj = this.stateObj;
    if (!stateObj) {
      return html`<div class="missing">
        ${this.entity} isn't available. Check that the ZoneMinder integration is
        loaded.
      </div>`;
    }
    const a = stateObj.attributes;
    const degrees = Number(a.orientation_degrees) || 0;
    const sideways = degrees === 90 || degrees === 270;
    const w = Number(a.width) || 16;
    const h = Number(a.height) || 9;
    const ratio = sideways ? `${h} / ${w}` : `${w} / ${h}`;
    const motion = this.motionState === "on";
    const unavailable = stateObj.state === "unavailable";

    return html`
      <figure class="tile ${motion ? "motion" : ""}" style="--ratio:${ratio}">
        <div
          class="frame"
          @click=${this.playing ? this.togglePause : this.moreInfo}
        >
          ${a.entity_picture
            ? html`<img class="still" alt="" src=${a.entity_picture} />`
            : nothing}
          <div
            class="turn ${this.liveShowing || this.playing ? "" : "waiting"}"
            style="--deg:${degrees}deg"
            ?data-sideways=${sideways}
          >
            ${!this.playing && this.visible && this.streamReady && !unavailable
              ? html`<ha-camera-stream
                  .hass=${this.hass}
                  .stateObj=${stateObj}
                  .muted=${true}
                  .controls=${false}
                  .allowExoPlayer=${true}
                  .fitMode=${"cover"}
                ></ha-camera-stream>`
              : nothing}
          </div>
          ${this.playing
            ? html`<video
                class="playback"
                muted
                playsinline
                preload="auto"
                poster=${this.playing.clip.event.thumbnail ?? nothing}
                src=${this.playing.clip.event.video!}
                @loadedmetadata=${this.onLoaded}
                @timeupdate=${this.onTimeUpdate}
                @ended=${this.onEnded}
              ></video>`
            : nothing}
          ${this.renderPlate(stateObj, motion, unavailable)}
          ${!this.playing && this.ptz && a.controllable
            ? this.renderPtz()
            : nothing}
        </div>
        ${this.playing
          ? html`<div class="transport">
              <button @click=${this.togglePause}>
                ${this.paused ? "Play" : "Pause"}
              </button>
              <button
                @click=${this.cycleSpeed}
                aria-label="Playback speed, now ${this.speed} times"
              >
                ${this.speed}×
              </button>
              <button class="live-btn" @click=${this.backToLive}>
                Back to live
              </button>
            </div>`
          : nothing}
        ${this.renderStrip()}
      </figure>
    `;
  }

  private renderPlate(
    stateObj: HassEntity,
    motion: boolean,
    unavailable: boolean,
  ) {
    const title = this.label ?? name(stateObj);
    if (this.playing) {
      return html`<figcaption class="plate">
        <span class="name">${title}</span>
        <span class="when">${this.clock.formatMoment(this.playing.at)}</span>
      </figcaption>`;
    }
    const status = unavailable
      ? "Offline"
      : motion
        ? "Motion"
        : stateObj.attributes.recording &&
            stateObj.attributes.recording !== "None"
          ? "Recording"
          : "Live";
    return html`<figcaption class="plate">
      <span class="name">${title}</span>
      <span class="status ${status.toLowerCase()}">${status}</span>
    </figcaption>`;
  }

  private renderPtz() {
    return html`<div class="ptz" @click=${(ev: Event) => ev.stopPropagation()}>
      ${this.ptzButton("up", "mdi:chevron-up", "Tilt up")}
      ${this.ptzButton("left", "mdi:chevron-left", "Pan left")}
      ${this.ptzButton("home", "mdi:crosshairs", "Go to home position")}
      ${this.ptzButton("right", "mdi:chevron-right", "Pan right")}
      ${this.ptzButton("down", "mdi:chevron-down", "Tilt down")}
    </div>`;
  }

  private renderStrip() {
    const { start, end } = this.span;
    const total = end - start;
    const x = (t: number) =>
      ((Math.min(Math.max(t, start), end) - start) / total) * 1000;
    const clips = this.clips;
    const bands = toBands(clips);
    const alarms = clips.filter((c) => c.event.alarm_frames > 0);
    const clock = this.clock;
    const ticks = clock.ticks(start, end);
    const marker = this.playing?.at ?? this.cursor;
    const hoverClip = this.hover?.clip;

    let empty: string | undefined;
    if (this.error) empty = `Couldn't load recordings: ${this.error}`;
    else if (this.window && clips.length === 0)
      empty = `No recordings in the last ${this.hours} hours`;

    const valueText =
      marker !== undefined
        ? `${clock.formatMoment(marker)}${this.clipAt(marker) ? "" : ", no recording"}`
        : "Live";

    return html`
      <div class="strip-wrap">
        <div
          class="strip"
          role="slider"
          tabindex="0"
          aria-label="Recordings, last ${this.hours} hours"
          aria-valuemin=${start}
          aria-valuemax=${end}
          aria-valuenow=${marker ?? end}
          aria-valuetext=${valueText}
          @pointermove=${this.onStripMove}
          @pointerleave=${() => (this.hover = undefined)}
          @click=${this.onStripClick}
          @keydown=${this.onStripKey}
          @blur=${() => (this.cursor = undefined)}
        >
          <svg
            viewBox="0 0 1000 40"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            ${ticks.map(
              (tick) =>
                svg`<line class="tick ${tick.midnight ? "midnight" : ""}" x1=${x(tick.t)} x2=${x(tick.t)} y1="0" y2="40" />`,
            )}
            ${bands.map(
              (b) =>
                svg`<rect class="band" x=${x(b.start)} width=${Math.max(x(b.end) - x(b.start), 1.5)} y="22" height="12" />`,
            )}
            ${alarms.map((c) => {
              const height = 6 + Math.min(c.event.max_score, 100) * 0.16;
              return svg`<rect class="alarm" x=${x(c.start)} width=${Math.max(x(c.end) - x(c.start), 2.5)} y=${34 - 12 - height} height=${height} />`;
            })}
            ${hoverClip
              ? svg`<rect class="hover-clip" x=${x(hoverClip.start)} width=${Math.max(x(hoverClip.end) - x(hoverClip.start), 1.5)} y="22" height="12" />`
              : nothing}
            ${marker !== undefined
              ? svg`<line class="marker" x1=${x(marker)} x2=${x(marker)} y1="4" y2="40" />`
              : nothing}
            <rect class="now" x="996" width="4" y="18" height="20" />
          </svg>
          ${this.hover ? this.renderPeek(this.hover) : nothing}
        </div>
        <div class="ticks" aria-hidden="true">
          ${ticks
            .filter((tick) => x(tick.t) > 30 && x(tick.t) < 900)
            .map(
              (tick) =>
                html`<span
                  style="left:${x(tick.t) / 10}%"
                  class=${tick.midnight ? "midnight" : ""}
                  >${tick.label}</span
                >`,
            )}
          <span class="now-label">Now</span>
        </div>
        ${empty ? html`<p class="empty">${empty}</p>` : nothing}
      </div>
    `;
  }

  private renderPeek(hover: { t: number; x: number; clip?: Clip }) {
    const clip = hover.clip;
    return html`<div class="peek" style="--x:${hover.x}px">
      ${clip?.event.thumbnail
        ? html`<img alt="" src=${clip.event.thumbnail} />`
        : nothing}
      <span>${this.clock.formatMoment(hover.t)}</span>
      ${clip ? nothing : html`<span class="gap">No recording</span>`}
      ${clip && clip.event.alarm_frames > 0
        ? html`<span class="cause"
            >${clip.event.notes?.trim() || clip.event.cause}</span
          >`
        : nothing}
    </div>`;
  }

  static styles = [
    tokens,
    css`
      :host {
        display: block;
        min-width: 0;
      }

      .tile {
        margin: 0;
        display: flex;
        flex-direction: column;
        background: var(--zm-kerb);
        border-radius: 10px;
        overflow: hidden;
        height: 100%;
      }

      .frame {
        position: relative;
        width: 100%;
        aspect-ratio: var(--ratio);
        /* Tall cameras would fill a phone screen on their own. */
        max-height: 70vh;
        background: #000;
        overflow: hidden;
        container-type: size;
        cursor: pointer;
      }

      .turn.waiting {
        opacity: 0;
      }
      .turn {
        position: absolute;
        inset: 0;
      }
      .turn[data-sideways] {
        inset: auto;
        left: 50%;
        top: 50%;
        width: 100cqh;
        height: 100cqw;
        transform: translate(-50%, -50%) rotate(var(--deg));
      }
      .turn:not([data-sideways]) {
        transform: rotate(var(--deg));
      }

      .still,
      .playback {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .turn > * {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      ha-camera-stream {
        --video-max-height: 100%;
      }

      /* The name plate sits on the picture like a caption on a monitor wall. */
      .plate {
        position: absolute;
        inset: auto 0 0 0;
        display: flex;
        align-items: baseline;
        gap: 12px;
        padding: 28px 14px 10px;
        background: linear-gradient(
          to top,
          rgba(10, 14, 17, 0.82),
          rgba(10, 14, 17, 0)
        );
        color: var(--zm-fog);
        font-family: var(--zm-font);
        pointer-events: none;
      }
      .plate > * {
        pointer-events: auto;
      }
      .name {
        font-size: 1.125rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .status,
      .when {
        font-size: 0.9375rem;
        font-variant-numeric: tabular-nums;
        color: var(--zm-concrete);
      }
      .status.motion {
        color: var(--zm-sodium);
        font-weight: 600;
      }
      .status.offline {
        color: var(--zm-fog);
      }
      .when {
        color: var(--zm-fog);
      }
      .tile.motion .plate {
        box-shadow: inset 4px 0 0 var(--zm-sodium);
      }

      .transport {
        display: flex;
        gap: 8px;
        padding: 10px 14px 0;
      }
      .transport .live-btn {
        margin-left: auto;
      }
      button {
        font: 500 0.9375rem/1 var(--zm-font);
        color: var(--zm-fog);
        background: transparent;
        border: 1px solid rgba(227, 231, 233, 0.22);
        border-radius: 6px;
        padding: 8px 14px;
        min-height: 36px;
        cursor: pointer;
      }
      button:hover {
        border-color: rgba(227, 231, 233, 0.45);
      }
      .live-btn {
        background: var(--zm-fog);
        color: var(--zm-asphalt);
        border-color: var(--zm-fog);
      }
      :focus-visible {
        outline: 2px solid var(--zm-sodium);
        outline-offset: 2px;
      }

      .ptz {
        position: absolute;
        top: 10px;
        right: 10px;
        display: grid;
        grid-template-areas: ". up ." "left home right" ". down .";
        gap: 2px;
        opacity: 0;
        transition: opacity 120ms;
      }
      .frame:hover .ptz,
      .ptz:focus-within {
        opacity: 1;
      }
      .ptz button {
        background: rgba(24, 32, 38, 0.8);
        min-height: 0;
        width: 34px;
        height: 34px;
        padding: 0;
        display: grid;
        place-items: center;
        --mdc-icon-size: 20px;
      }
      .ptz-up {
        grid-area: up;
      }
      .ptz-down {
        grid-area: down;
      }
      .ptz-left {
        grid-area: left;
      }
      .ptz-right {
        grid-area: right;
      }
      .ptz-home {
        grid-area: home;
      }

      /* The strip: what this camera saw over the last day. */
      .strip-wrap {
        position: relative;
        padding: 10px 14px 12px;
        font-family: var(--zm-font);
      }
      .strip {
        position: relative;
        height: 40px;
        cursor: crosshair;
        border-radius: 4px;
        touch-action: none;
      }
      .strip svg {
        width: 100%;
        height: 100%;
        display: block;
        overflow: visible;
      }
      .tick {
        stroke: rgba(126, 136, 144, 0.28);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
      }
      .tick.midnight {
        stroke: rgba(126, 136, 144, 0.6);
      }
      .band {
        fill: var(--zm-tape);
      }
      .hover-clip {
        fill: #5d8fae;
      }
      .alarm {
        fill: var(--zm-sodium);
      }
      .marker {
        stroke: var(--zm-sodium);
        stroke-width: 2;
        vector-effect: non-scaling-stroke;
      }
      .now {
        fill: var(--zm-concrete);
      }
      .tile.motion .now {
        fill: var(--zm-sodium);
        animation: breathe 1.6s ease-in-out infinite;
      }
      @keyframes breathe {
        50% {
          opacity: 0.35;
        }
      }

      .ticks {
        position: relative;
        height: 16px;
        margin-top: 4px;
        font-size: 0.8125rem;
        color: var(--zm-concrete);
        font-variant-numeric: tabular-nums;
      }
      .ticks span {
        position: absolute;
        transform: translateX(-50%);
        white-space: nowrap;
      }
      .ticks span.midnight {
        color: var(--zm-fog);
      }
      .ticks .now-label {
        right: 0;
        transform: none;
      }

      .peek {
        position: absolute;
        bottom: calc(100% + 8px);
        left: clamp(80px, var(--x), calc(100% - 80px));
        transform: translateX(-50%);
        width: 160px;
        display: flex;
        flex-direction: column;
        gap: 2px;
        padding: 4px 4px 6px;
        background: var(--zm-asphalt);
        border: 1px solid rgba(227, 231, 233, 0.16);
        border-radius: 6px;
        color: var(--zm-fog);
        font-size: 0.875rem;
        font-variant-numeric: tabular-nums;
        pointer-events: none;
        z-index: 2;
      }
      .peek img {
        width: 100%;
        aspect-ratio: var(--ratio);
        max-height: 180px;
        object-fit: cover;
        border-radius: 3px;
        background: #000;
      }
      .peek span {
        padding: 0 4px;
      }
      .peek .gap,
      .peek .cause {
        color: var(--zm-concrete);
      }
      .peek .cause {
        color: var(--zm-sodium);
      }

      .empty {
        margin: 6px 0 0;
        color: var(--zm-concrete);
        font-size: 0.875rem;
      }
      .missing {
        padding: 16px;
        color: var(--zm-concrete);
        font-family: var(--zm-font);
      }

      @media (prefers-reduced-motion: reduce) {
        .tile.motion .now {
          animation: none;
        }
        .ptz {
          transition: none;
        }
      }
    `,
  ];
}

// ---------------------------------------------------------------------------
// The card
// ---------------------------------------------------------------------------

export class ZoneMinderCard extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private config!: ZoneMinderCardConfig;

  static getStubConfig(): Partial<ZoneMinderCardConfig> {
    return {};
  }

  setConfig(config: ZoneMinderCardConfig): void {
    if (
      config.hours !== undefined &&
      (config.hours < 1 || config.hours > 168)
    ) {
      throw new Error("hours must be between 1 and 168");
    }
    this.config = config;
    requestFont();
  }

  getCardSize(): number {
    return 6 * Math.ceil(this.cameras.length / (this.config?.columns ?? 2));
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  private get cameras(): Array<{ entity: string; name?: string }> {
    if (!this.hass) return [];
    if (this.config?.entities?.length) {
      return this.config.entities.map((e) =>
        typeof e === "string" ? { entity: e } : e,
      );
    }
    return zoneminderCameras(this.hass).map((entity) => ({ entity }));
  }

  protected render() {
    const cameras = this.cameras;
    const columns = this.config.columns;
    return html`
      <ha-card>
        ${cameras.length
          ? html`<div
              class="wall"
              style=${columns
                ? `grid-template-columns: repeat(${columns}, minmax(0, 1fr))`
                : ""}
            >
              ${cameras.map(
                (c) =>
                  html`<zm-camera-tile
                    .hass=${this.hass}
                    .entity=${c.entity}
                    .label=${c.name}
                    .hours=${this.config.hours ?? DEFAULT_HOURS}
                    .ptz=${this.config.ptz ?? true}
                    class=${this.isSideways(c.entity) ? "tall" : ""}
                  ></zm-camera-tile>`,
              )}
            </div>`
          : html`<p class="none">
              No ZoneMinder cameras yet. Add the ZoneMinder integration under
              Settings, then Devices & services.
            </p>`}
      </ha-card>
    `;
  }

  private isSideways(entity: string): boolean {
    const deg =
      Number(this.hass.states[entity]?.attributes.orientation_degrees) || 0;
    return deg === 90 || deg === 270;
  }

  static styles = [
    tokens,
    css`
      ha-card {
        background: var(--zm-asphalt);
        padding: 12px;
        border-radius: var(--ha-card-border-radius, 12px);
        overflow: visible;
      }
      .wall {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(min(340px, 100%), 1fr));
        grid-auto-flow: row dense;
        gap: 12px;
        align-items: start;
      }
      .none {
        margin: 0;
        padding: 8px 4px;
        color: var(--zm-fog);
        font-family: var(--zm-font);
      }
    `,
  ];
}

// The integration loads this card on every dashboard, and older setups may
// also list it as a manual resource. The second copy must step aside quietly.
if (!customElements.get("zoneminder-card")) {
  customElements.define("zm-camera-tile", ZmCameraTile);
  customElements.define("zoneminder-card", ZoneMinderCard);
  registerCardPicker();
}

function registerCardPicker(): void {
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "zoneminder-card",
    name: "ZoneMinder",
    description:
      "Live cameras with a day of recordings under each one. Click the strip to play back.",
    preview: true,
  });
}
