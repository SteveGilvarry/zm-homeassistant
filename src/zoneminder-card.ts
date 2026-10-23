import { LitElement, html, css, PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { HomeAssistant, ZoneMinerCardConfig, MonitorConfig } from './types';
import './webrtc-player';

// Window interface extension for card registration
declare global {
  interface Window {
    customCards?: any[];
  }
}

// Register card with Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'zoneminder-card',
  name: 'ZoneMinder Card',
  description: 'Display ZoneMinder cameras with direct go2rtc WebRTC streaming',
  preview: false,
  documentationURL: 'https://github.com/yourusername/zoneminder-card',
});

@customElement('zoneminder-card')
export class ZoneMinerCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @state() private _config!: ZoneMinerCardConfig;
  @state() private _go2rtcUrl = '';
  @state() private _editMode = false;
  @state() private _draggedIndex: number | null = null;

  static styles = css`
    :host {
      display: block;
      padding: 16px;
    }

    .card-header {
      font-size: 24px;
      font-weight: 400;
      padding: 0 0 16px 0;
      color: var(--primary-text-color);
      font-family: var(--paper-font-headline_-_font-family);
    }

    .grid {
      display: grid;
      gap: 8px;
      width: 100%;
      grid-auto-flow: dense;
    }

    .monitor {
      position: relative;
      background: #000;
      border-radius: 4px;
      overflow: hidden;
      width: 100%;
    }

    .monitor.motion-active {
      outline: 3px solid var(--error-color, #ff5252);
      outline-offset: -3px;
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% {
        outline-color: var(--error-color, #ff5252);
      }
      50% {
        outline-color: rgba(255, 82, 82, 0.5);
      }
    }

    .monitor-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      pointer-events: none;
      z-index: 10;
    }

    .motion-indicator {
      position: absolute;
      top: 8px;
      left: 8px;
      background: var(--error-color, #ff5252);
      color: white;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
      animation: fadeIn 0.3s ease-in-out;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(-4px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .motion-dot {
      width: 8px;
      height: 8px;
      background: white;
      border-radius: 50%;
      animation: blink 1s ease-in-out infinite;
    }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }

    .monitor-name {
      position: absolute;
      bottom: 8px;
      left: 8px;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
    }

    .controls {
      position: absolute;
      bottom: 8px;
      right: 8px;
      display: flex;
      gap: 4px;
      pointer-events: auto;
    }

    .control-button {
      background: rgba(0, 0, 0, 0.7);
      color: white;
      border: none;
      border-radius: 4px;
      padding: 8px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .control-button:hover {
      background: rgba(0, 0, 0, 0.9);
    }

    .control-button:active {
      transform: scale(0.95);
    }

    webrtc-player {
      width: 100%;
      height: 100%;
    }

    .error {
      padding: 16px;
      background: var(--error-color, #ff5252);
      color: white;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .warning {
      padding: 16px;
      background: var(--warning-color, #ff9800);
      color: white;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .edit-toggle {
      background: var(--primary-color, #03a9f4);
      color: white;
      border: none;
      border-radius: 4px;
      padding: 8px 16px;
      font-size: 14px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .edit-toggle:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    .edit-toggle.active {
      background: var(--success-color, #4caf50);
    }

    .monitor.edit-mode {
      cursor: grab;
      outline: 2px dashed var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .monitor.edit-mode:hover {
      outline-color: var(--accent-color, #ff9800);
    }

    .monitor.dragging {
      opacity: 0.5;
      cursor: grabbing;
    }

    .monitor.drag-over {
      outline: 3px solid var(--accent-color, #ff9800);
      outline-offset: 2px;
    }
  `;

  public setConfig(config: ZoneMinerCardConfig): void {
    if (!config.monitors || config.monitors.length === 0) {
      throw new Error('You must specify at least one monitor');
    }

    // Apply default config
    let monitors = config.monitors;

    // Try to restore saved monitor order from localStorage
    const savedOrder = this._loadMonitorOrder(config.monitors);
    if (savedOrder) {
      monitors = savedOrder;
    }

    this._config = {
      columns: 4,  // Even number for portrait/landscape spanning
      aspect_ratio: '16:9',
      streaming_mode: 'webrtc',
      show_motion_indicator: true,
      show_controls: false,
      refresh_interval: 1000,
      click_action: 'fullscreen',
      ...config,
      monitors,
    };
  }

  private _getStorageKey(monitors: MonitorConfig[]): string {
    // Create a unique key based on the monitor entities (sorted for consistency)
    const entities = monitors.map(m => m.entity).sort().join(',');
    return `zoneminder-card-order:${entities}`;
  }

  private _loadMonitorOrder(originalMonitors: MonitorConfig[]): MonitorConfig[] | null {
    try {
      const key = this._getStorageKey(originalMonitors);
      const saved = localStorage.getItem(key);
      if (!saved) return null;

      const savedEntities: string[] = JSON.parse(saved);

      // Validate saved order has same entities
      const originalEntities = new Set(originalMonitors.map(m => m.entity));
      const savedSet = new Set(savedEntities);
      if (originalEntities.size !== savedSet.size) return null;
      for (const entity of originalEntities) {
        if (!savedSet.has(entity)) return null;
      }

      // Reorder monitors based on saved order
      const monitorMap = new Map(originalMonitors.map(m => [m.entity, m]));
      return savedEntities.map(entity => monitorMap.get(entity)!);
    } catch {
      return null;
    }
  }

  private _saveMonitorOrder(monitors: MonitorConfig[]): void {
    try {
      const key = this._getStorageKey(monitors);
      const entities = monitors.map(m => m.entity);
      localStorage.setItem(key, JSON.stringify(entities));
    } catch {
      // Ignore storage errors
    }
  }

  public getCardSize(): number {
    const rows = Math.ceil((this._config?.monitors?.length || 1) / (this._config?.columns || 2));
    return rows * 3; // Each row is roughly 3 units
  }

  protected updated(changedProperties: PropertyValues): void {
    super.updated(changedProperties);

    if (changedProperties.has('hass') && this.hass) {
      this._detectGo2rtcUrl();
    }
  }

  /**
   * Determine if a camera is portrait orientation (rotated 90 or 270 degrees)
   */
  private _isPortraitCamera(cameraEntity: any): boolean {
    const orientation = cameraEntity?.attributes?.orientation || 'ROTATE_0';
    const normalized = this._normalizeOrientation(orientation);
    return normalized === 'ROTATE_90' || normalized === 'ROTATE_270';
  }

  /**
   * Get the column span for a monitor based on orientation
   * Portrait cameras span 1 column, landscape cameras span 2 columns
   */
  private _getColumnSpan(monitorConfig: MonitorConfig): number {
    // Allow explicit override in monitor config
    if (monitorConfig.columns) {
      return monitorConfig.columns;
    }

    const cameraEntity = this.hass?.states[monitorConfig.entity];
    if (!cameraEntity) return 1;

    // Portrait = 1 column, Landscape = 2 columns
    return this._isPortraitCamera(cameraEntity) ? 1 : 2;
  }

  render() {
    if (!this._config || !this.hass) {
      return html``;
    }

    if (!this._go2rtcUrl) {
      return html`
        <div class="warning">
          <strong>Warning:</strong> go2rtc URL not configured or auto-detected.<br />
          Please configure <code>zoneminder_go2rtc_url</code> in card configuration.
        </div>
      `;
    }

    const columns = this._config.columns || 4;

    return html`
      <div class="header-row">
        <div class="card-header" style="padding: 0; margin: 0;">
          ${this._config.title || ''}
        </div>
        <button
          class="edit-toggle ${this._editMode ? 'active' : ''}"
          @click=${this._toggleEditMode}
        >
          ${this._editMode ? 'Done' : 'Edit Layout'}
        </button>
      </div>
      <div class="grid" style="grid-template-columns: repeat(${columns}, 1fr)">
        ${this._config.monitors.map((monitor, index) => this._renderMonitor(monitor, index))}
      </div>
    `;
  }

  private _toggleEditMode(): void {
    this._editMode = !this._editMode;
    if (!this._editMode) {
      this._draggedIndex = null;
    }
  }

  private _renderMonitor(monitorConfig: MonitorConfig, index: number) {
    const cameraEntity = this.hass.states[monitorConfig.entity];
    const columnSpan = this._getColumnSpan(monitorConfig);
    const isDragging = this._draggedIndex === index;

    if (!cameraEntity) {
      // No aspect ratio for error state - let it auto-size
      return html`
        <div
          class="monitor ${this._editMode ? 'edit-mode' : ''}"
          style="grid-column: span ${columnSpan}; min-height: 100px"
          draggable=${this._editMode}
          @dragstart=${(e: DragEvent) => this._handleDragStart(e, index)}
          @dragover=${(e: DragEvent) => this._handleDragOver(e, index)}
          @dragleave=${(e: DragEvent) => this._handleDragLeave(e)}
          @drop=${(e: DragEvent) => this._handleDrop(e, index)}
          @dragend=${this._handleDragEnd}
        >
          <div class="error" style="margin: 0; height: 100%; display: flex; align-items: center; justify-content: center;">
            Entity ${monitorConfig.entity} not found
          </div>
        </div>
      `;
    }

    // Get video dimensions from entity attributes
    const videoWidth = Number(cameraEntity.attributes.width) || 0;
    const videoHeight = Number(cameraEntity.attributes.height) || 0;

    // Get orientation and determine if portrait
    const rawOrientation = cameraEntity.attributes.orientation || 'ROTATE_0';
    const orientation = this._normalizeOrientation(rawOrientation);
    const isPortrait = this._isPortraitCamera(cameraEntity);

    // Calculate aspect ratio based on dimensions and orientation
    const aspectRatio = this._getAspectRatioCss(videoWidth, videoHeight, isPortrait);

    // Get stream ID from config or entity attributes
    const streamId =
      monitorConfig.stream_id ||
      cameraEntity.attributes.go2rtc_stream_id ||
      cameraEntity.attributes.monitor_id;

    if (!streamId) {
      return html`
        <div
          class="monitor ${this._editMode ? 'edit-mode' : ''}"
          style="grid-column: span ${columnSpan}; aspect-ratio: ${aspectRatio}"
          draggable=${this._editMode}
          @dragstart=${(e: DragEvent) => this._handleDragStart(e, index)}
          @dragover=${(e: DragEvent) => this._handleDragOver(e, index)}
          @dragleave=${(e: DragEvent) => this._handleDragLeave(e)}
          @drop=${(e: DragEvent) => this._handleDrop(e, index)}
          @dragend=${this._handleDragEnd}
        >
          <div class="error" style="margin: 0; height: 100%; display: flex; align-items: center; justify-content: center;">
            No stream ID found for ${monitorConfig.entity}
          </div>
        </div>
      `;
    }

    // Check for motion
    const motionEntityId = monitorConfig.entity.replace('camera.', 'binary_sensor.') + '_motion';
    const motionEntity = this.hass.states[motionEntityId];
    const isMotion = motionEntity?.state === 'on';

    // Get monitor name
    const monitorName =
      monitorConfig.name || cameraEntity.attributes.friendly_name || monitorConfig.entity;

    // Build class list
    const classes = ['monitor'];
    if (isMotion) classes.push('motion-active');
    if (this._editMode) classes.push('edit-mode');
    if (isDragging) classes.push('dragging');

    return html`
      <div
        class=${classes.join(' ')}
        style="grid-column: span ${columnSpan}; aspect-ratio: ${aspectRatio}"
        draggable=${this._editMode}
        @dragstart=${(e: DragEvent) => this._handleDragStart(e, index)}
        @dragover=${(e: DragEvent) => this._handleDragOver(e, index)}
        @dragleave=${(e: DragEvent) => this._handleDragLeave(e)}
        @drop=${(e: DragEvent) => this._handleDrop(e, index)}
        @dragend=${this._handleDragEnd}
        @click=${() => !this._editMode && this._handleClick(monitorConfig)}
      >
        <webrtc-player
          .go2rtcUrl=${this._go2rtcUrl}
          .streamId=${String(streamId)}
          .mode=${this._config.streaming_mode || 'webrtc'}
          .orientation=${orientation}
          .videoWidth=${videoWidth}
          .videoHeight=${videoHeight}
        ></webrtc-player>

        <div class="monitor-overlay">
          ${this._config.show_motion_indicator && isMotion
            ? html`
                <div class="motion-indicator">
                  <div class="motion-dot"></div>
                  <span>Motion Detected</span>
                </div>
              `
            : ''}

          <div class="monitor-name">${monitorName}</div>

          ${this._config.show_controls
            ? html`
                <div class="controls">
                  <button
                    class="control-button"
                    @click=${(e: Event) => this._handleFullscreen(e, monitorConfig)}
                    title="Fullscreen"
                  >
                    ⛶
                  </button>
                </div>
              `
            : ''}
        </div>
      </div>
    `;
  }

  private _getAspectRatioCss(videoWidth: number, videoHeight: number, isPortrait: boolean): string {
    // Always calculate from actual video dimensions
    // For portrait cameras (rotated 90/270), swap width and height
    if (isPortrait) {
      return `${videoHeight} / ${videoWidth}`;
    }
    return `${videoWidth} / ${videoHeight}`;
  }

  private _normalizeOrientation(orientation: string): string {
    // Normalize various orientation formats to ZoneMinder standard: ROTATE_0, ROTATE_90, ROTATE_180, ROTATE_270
    switch (orientation) {
      case 'ROTATE_90':
      case 'Rotate Right':
        return 'ROTATE_90';
      case 'ROTATE_180':
      case 'Inverted':
        return 'ROTATE_180';
      case 'ROTATE_270':
      case 'Rotate Left':
        return 'ROTATE_270';
      case 'ROTATE_0':
      case 'Normal':
      default:
        return 'ROTATE_0';
    }
  }

  private _detectGo2rtcUrl(): void {
    // Try to auto-detect go2rtc URL from integration
    if (this._config.zoneminder_go2rtc_url) {
      this._go2rtcUrl = this._config.zoneminder_go2rtc_url;
      return;
    }

    // Look for go2rtc URL in any camera entity attributes
    for (const monitor of this._config.monitors) {
      const entity = this.hass.states[monitor.entity];
      if (entity?.attributes.go2rtc_url) {
        this._go2rtcUrl = entity.attributes.go2rtc_url;
        return;
      }
    }

    // Fallback: Try to find zoneminder integration data
    // This would require the integration to expose go2rtc URL as a sensor or in device attributes
  }

  private _handleClick(monitorConfig: MonitorConfig): void {
    if (this._config.click_action === 'fullscreen') {
      this._handleFullscreen(new Event('click'), monitorConfig);
    } else if (this._config.click_action === 'events') {
      // Navigate to events page (would need to implement)
      this._navigateToEvents(monitorConfig);
    }
    // Default: do nothing (don't open more-info dialog with MPEG stream)
  }

  private _handleFullscreen(e: Event, monitorConfig: MonitorConfig): void {
    e.stopPropagation();
    // TODO: Implement custom fullscreen view with WebRTC stream
    // For now, do nothing to avoid opening the MPEG-based more-info dialog
    console.log('Fullscreen requested for', monitorConfig.entity);
  }

  // Drag and drop handlers
  private _handleDragStart(e: DragEvent, index: number): void {
    if (!this._editMode) return;
    this._draggedIndex = index;
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', String(index));
    }
    // Add dragging class after a brief delay to allow the drag image to be created
    requestAnimationFrame(() => {
      this.requestUpdate();
    });
  }

  private _handleDragOver(e: DragEvent, index: number): void {
    if (!this._editMode || this._draggedIndex === null) return;
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'move';
    }
    // Add visual feedback for drag target
    const target = e.currentTarget as HTMLElement;
    if (index !== this._draggedIndex) {
      target.classList.add('drag-over');
    }
  }

  private _handleDragLeave(e: DragEvent): void {
    const target = e.currentTarget as HTMLElement;
    target.classList.remove('drag-over');
  }

  private _handleDrop(e: DragEvent, targetIndex: number): void {
    e.preventDefault();
    if (!this._editMode || this._draggedIndex === null) return;

    const target = e.currentTarget as HTMLElement;
    target.classList.remove('drag-over');

    if (this._draggedIndex !== targetIndex) {
      this._reorderMonitors(this._draggedIndex, targetIndex);
    }
    this._draggedIndex = null;
  }

  private _handleDragEnd(): void {
    this._draggedIndex = null;
    // Remove any lingering drag-over classes
    const dragOverElements = this.shadowRoot?.querySelectorAll('.drag-over');
    dragOverElements?.forEach(el => el.classList.remove('drag-over'));
    this.requestUpdate();
  }

  private _reorderMonitors(fromIndex: number, toIndex: number): void {
    // Create a new monitors array with the reordered items
    const monitors = [...this._config.monitors];
    const [movedMonitor] = monitors.splice(fromIndex, 1);
    monitors.splice(toIndex, 0, movedMonitor);

    // Update config and dispatch event for Home Assistant to persist
    const newConfig = { ...this._config, monitors };
    this._config = newConfig;

    // Save to localStorage for persistence across page refreshes
    this._saveMonitorOrder(monitors);

    // Dispatch config-changed event for HA to persist (works when dashboard is in edit mode)
    const event = new CustomEvent('config-changed', {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  private _navigateToEvents(monitorConfig: MonitorConfig): void {
    // TODO: Implement navigation to events
    console.log('Navigate to events for', monitorConfig.entity);
  }

  static getConfigElement() {
    return document.createElement('zoneminder-card-editor');
  }

  static getStubConfig() {
    return {
      type: 'custom:zoneminder-card',
      title: 'Security Cameras',
      monitors: [
        { entity: 'camera.front_door' },
        { entity: 'camera.backyard' },
      ],
      columns: 4,
      streaming_mode: 'webrtc',
      show_motion_indicator: true,
    };
  }
}
