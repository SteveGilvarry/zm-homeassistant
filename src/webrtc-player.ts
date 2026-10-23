import { LitElement, html, css, PropertyValues } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import { StreamingMode, WebRTCMessage } from './types';

@customElement('webrtc-player')
export class WebRTCPlayer extends LitElement {
  @property({ type: String }) go2rtcUrl = '';
  @property({ type: String }) streamId = '';
  @property({ type: String }) mode: StreamingMode = 'webrtc';
  @property({ type: String }) orientation = 'ROTATE_0';
  @property({ type: Number }) videoWidth = 0;
  @property({ type: Number }) videoHeight = 0;
  @property({ type: Boolean }) autoplay = true;
  @property({ type: Boolean }) muted = true;

  @state() private _connected = false;
  @state() private _error: string | null = null;

  @query('video') private _video?: HTMLVideoElement;

  private _pc?: RTCPeerConnection;
  private _ws?: WebSocket;

  static styles = css`
    :host {
      display: block;
      position: relative;
      width: 100%;
      height: 100%;
      background: #000;
      overflow: hidden;
    }

    video {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: contain;
      transform-origin: center center;
    }

    /*
     * For 90° and 270° rotations, we need to scale the video to compensate
     * for letterboxing. The scale factor equals the video's aspect ratio.
     * This is applied via inline style with CSS variable --video-scale.
     */
    video.rotate-90 {
      transform: rotate(90deg) scale(var(--video-scale, 1));
    }

    video.rotate-180 {
      transform: rotate(180deg);
    }

    video.rotate-270 {
      transform: rotate(270deg) scale(var(--video-scale, 1));
    }

    .error {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #ff5252;
      background: rgba(0, 0, 0, 0.8);
      padding: 16px;
      border-radius: 4px;
      text-align: center;
      font-family: system-ui, -apple-system, sans-serif;
    }

    .loading {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #fff;
      font-family: system-ui, -apple-system, sans-serif;
    }

    .spinner {
      border: 3px solid rgba(255, 255, 255, 0.3);
      border-top: 3px solid #fff;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
      margin: 0 auto 16px;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `;

  render() {
    const orientationClass = this._getOrientationClass();
    const videoStyle = this._getVideoStyle();

    return html`
      <video
        class="${orientationClass}"
        style="${videoStyle}"
        ?autoplay=${this.autoplay}
        ?muted=${this.muted}
        playsinline
        @loadedmetadata=${this._handleVideoLoaded}
      ></video>
      ${!this._connected && !this._error
        ? html`
            <div class="loading">
              <div class="spinner"></div>
              <div>Connecting...</div>
            </div>
          `
        : ''}
      ${this._error
        ? html`
            <div class="error">
              <div>Connection Error</div>
              <div style="font-size: 12px; margin-top: 8px;">${this._error}</div>
            </div>
          `
        : ''}
    `;
  }

  private _getOrientationClass(): string {
    // Only use ZoneMinder rotation values: ROTATE_0, ROTATE_90, ROTATE_180, ROTATE_270
    switch (this.orientation) {
      case 'ROTATE_90':
        return 'rotate-90';
      case 'ROTATE_180':
        return 'rotate-180';
      case 'ROTATE_270':
        return 'rotate-270';
      case 'ROTATE_0':
      default:
        return '';
    }
  }

  private _getVideoStyle(): string {
    // For 90° and 270° rotations, calculate scale factor to eliminate letterboxing
    // Scale factor = video aspect ratio (width / height)
    if (
      (this.orientation === 'ROTATE_90' || this.orientation === 'ROTATE_270') &&
      this.videoWidth > 0 &&
      this.videoHeight > 0
    ) {
      const aspectRatio = this.videoWidth / this.videoHeight;
      return `--video-scale: ${aspectRatio}`;
    }
    return '';
  }

  protected updated(changedProperties: PropertyValues): void {
    super.updated(changedProperties);

    if (
      changedProperties.has('go2rtcUrl') ||
      changedProperties.has('streamId') ||
      changedProperties.has('mode')
    ) {
      this._reconnect();
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.disconnect();
  }

  public async connect(): Promise<void> {
    if (!this.go2rtcUrl || !this.streamId) {
      this._error = 'Missing go2rtc URL or stream ID';
      return;
    }

    this._error = null;

    switch (this.mode) {
      case 'webrtc':
        await this._connectWebRTC();
        break;
      case 'mse':
        this._connectMSE();
        break;
      case 'hls':
        this._connectHLS();
        break;
      case 'mjpeg':
        this._connectMJPEG();
        break;
    }
  }

  public disconnect(): void {
    if (this._ws) {
      this._ws.close();
      this._ws = undefined;
    }

    if (this._pc) {
      this._pc.close();
      this._pc = undefined;
    }

    if (this._video) {
      this._video.srcObject = null;
      this._video.src = '';
    }

    this._connected = false;
  }

  private _reconnect(): void {
    this.disconnect();
    this.connect();
  }

  private async _connectWebRTC(): Promise<void> {
    try {
      this._pc = new RTCPeerConnection({
        iceServers: [
          { urls: ['stun:stun.cloudflare.com:3478'] },
          { urls: ['stun:stun.l.google.com:19302'] },
        ],
      });

      // Add transceivers for receiving video and audio
      this._pc.addTransceiver('video', { direction: 'recvonly' });
      this._pc.addTransceiver('audio', { direction: 'recvonly' });

      // Handle incoming tracks
      this._pc.ontrack = (ev) => {
        if (this._video) {
          this._video.srcObject = ev.streams[0];
          this._connected = true;
        }
      };

      // Handle connection state changes
      this._pc.onconnectionstatechange = () => {
        if (this._pc?.connectionState === 'failed') {
          this._error = 'WebRTC connection failed';
          this.disconnect();
        }
      };

      // Connect WebSocket for signaling
      const wsUrl =
        this.go2rtcUrl.replace('http://', 'ws://').replace('https://', 'wss://') +
        `/api/ws?src=${this.streamId}`;

      this._ws = new WebSocket(wsUrl);

      this._ws.onopen = () => {
        // Handle ICE candidates
        if (this._pc) {
          this._pc.onicecandidate = (ev) => {
            if (ev.candidate && this._ws?.readyState === WebSocket.OPEN) {
              const msg: WebRTCMessage = {
                type: 'webrtc/candidate',
                value: ev.candidate.candidate,
              };
              this._ws.send(JSON.stringify(msg));
            }
          };

          // Create and send offer
          this._pc
            .createOffer()
            .then((offer) => this._pc!.setLocalDescription(offer))
            .then(() => {
              const msg: WebRTCMessage = {
                type: 'webrtc/offer',
                value: this._pc!.localDescription!.sdp,
              };
              this._ws!.send(JSON.stringify(msg));
            })
            .catch((err) => {
              this._error = `Failed to create offer: ${err.message}`;
            });
        }
      };

      this._ws.onmessage = (ev) => {
        const msg: WebRTCMessage = JSON.parse(ev.data);

        if (msg.type === 'webrtc/candidate' && this._pc) {
          this._pc.addIceCandidate({ candidate: msg.value, sdpMid: '0' }).catch((err) => {
            console.warn('Failed to add ICE candidate:', err);
          });
        } else if (msg.type === 'webrtc/answer' && this._pc) {
          this._pc.setRemoteDescription({ type: 'answer', sdp: msg.value }).catch((err) => {
            this._error = `Failed to set remote description: ${err.message}`;
          });
        }
      };

      this._ws.onerror = (ev) => {
        this._error = 'WebSocket connection failed';
        this.disconnect();
      };

      this._ws.onclose = () => {
        if (this._connected) {
          // Connection was established then dropped - attempt reconnect
          setTimeout(() => this._reconnect(), 5000);
        }
      };
    } catch (err: any) {
      this._error = `WebRTC error: ${err.message}`;
    }
  }

  private _connectMSE(): void {
    if (!this._video) return;

    const url = `${this.go2rtcUrl}/api/stream.mp4?src=${this.streamId}`;
    this._video.src = url;
    this._connected = true;
  }

  private _connectHLS(): void {
    if (!this._video) return;

    const url = `${this.go2rtcUrl}/api/stream.m3u8?src=${this.streamId}`;
    this._video.src = url;
    this._connected = true;
  }

  private _connectMJPEG(): void {
    if (!this._video) return;

    const url = `${this.go2rtcUrl}/api/stream.mjpeg?src=${this.streamId}`;

    // MJPEG uses an img tag wrapped in srcObject trick
    const img = new Image();
    img.src = url;
    img.onload = () => {
      this._connected = true;
    };
    img.onerror = () => {
      this._error = 'Failed to load MJPEG stream';
    };

    // Note: For MJPEG, we'd typically use an <img> element instead of <video>
    // For now, we'll just set the src directly (browser support varies)
    this._video.poster = url;
  }

  private _handleVideoLoaded(): void {
    // Video metadata loaded successfully
    this._connected = true;
  }
}
