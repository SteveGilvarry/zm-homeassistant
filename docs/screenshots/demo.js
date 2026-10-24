// In-page helpers for the README screenshots, injected by take.py.
//
// Everything on screen stays the real Home Assistant frontend and the real
// zoneminder-card. What's staged is the data: the card gets made-up cameras
// and a generated day of events, and the device page has its names and server
// address swapped, so no real camera, name or address is ever shown.

(() => {
  /** querySelectorAll that also searches every open shadow root. */
  function deep(selector, root = document) {
    const found = [];
    const stack = [root];
    while (stack.length) {
      const node = stack.pop();
      if (!node.querySelectorAll) continue;
      node.querySelectorAll(selector).forEach((el) => found.push(el));
      node.querySelectorAll("*").forEach((el) => el.shadowRoot && stack.push(el.shadowRoot));
    }
    return found;
  }

  const hass = () => document.querySelector("home-assistant").hass;

  /** Seeded random numbers, so every run draws the same day of events. */
  function seeded(seed) {
    return () => {
      seed = (seed * 16807) % 2147483647;
      return seed / 2147483647;
    };
  }

  const CAMERAS = [
    { id: "driveway", name: "Driveway", recording: "OnMotion", motion: "off", continuous: false },
    { id: "front_door", name: "Front door", recording: "OnMotion", motion: "on", continuous: false },
    { id: "car_park", name: "Car park", recording: "Always", motion: "off", continuous: true },
    { id: "back_yard", name: "Back yard", recording: "Always", motion: "off", continuous: true },
  ];
  const HOUR = 3_600_000;

  /** A day of events for one camera, shaped like `zoneminder/events` returns. */
  function eventsFor(camera, frameUrl, now, random) {
    const events = [];
    let id = 1000 + CAMERAS.indexOf(camera) * 500;
    const add = (start, length, motion, inProgress = false) =>
      events.push({
        id: id++,
        start: new Date(start).toISOString(),
        end: inProgress ? null : new Date(start + length).toISOString(),
        length: inProgress ? 0 : length / 1000,
        cause: motion ? "Motion" : "Continuous",
        notes: null,
        alarm_frames: motion ? 5 + Math.floor(random() * 60) : 0,
        max_score: motion ? 20 + Math.floor(random() * 80) : 0,
        in_progress: inProgress,
        thumbnail: frameUrl,
        video: inProgress ? null : frameUrl,
      });

    if (camera.continuous) {
      // Ten-minute chunks all day, with an hour-long gap overnight.
      for (let t = now - 24 * HOUR; t < now - 600_000; t += 600_000) {
        const hoursAgo = (now - t) / HOUR;
        if (hoursAgo > 13.2 && hoursAgo < 14.6) continue;
        add(t, 600_000, false);
      }
      add(now - 600_000, 0, false, true);
      for (let i = 0; i < 9; i++) add(now - (1 + random() * 22) * HOUR, 20_000 + random() * 60_000, true);
    } else {
      const count = camera.motion === "on" ? 16 : 11;
      for (let i = 0; i < count; i++) {
        const hoursAgo = random() < 0.6 ? 1 + random() * 9 : 9 + random() * 14;
        add(now - hoursAgo * HOUR, 15_000 + random() * 90_000, true);
      }
      if (camera.motion === "on") add(now - 40_000, 0, true, true);
    }
    events.sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
    return { start: new Date(now - 24 * HOUR).toISOString(), end: new Date(now).toISOString(), events };
  }

  /**
   * Put a zoneminder-card with made-up cameras over the current view.
   * `frames` maps camera id to an image URL. Returns the card element.
   */
  async function mountCard(frames, { width = 930 } = {}) {
    await customElements.whenDefined("zoneminder-card");
    const real = hass();
    const random = seeded(7);
    const now = Date.now();
    const states = {};
    const entities = {};
    const windows = {};
    for (const camera of CAMERAS) {
      const cameraId = `camera.${camera.id}`;
      const motionId = `binary_sensor.${camera.id}_motion`;
      const device = `demo_${camera.id}`;
      states[cameraId] = {
        entity_id: cameraId,
        state: camera.recording === "Always" ? "recording" : "streaming",
        attributes: {
          friendly_name: camera.name,
          entity_picture: frames[camera.id],
          width: 1920,
          height: 1080,
          orientation_degrees: 0,
          recording: camera.recording,
          controllable: false,
        },
        last_changed: "",
        last_updated: "",
      };
      states[motionId] = {
        entity_id: motionId,
        state: camera.motion,
        attributes: { friendly_name: `${camera.name} motion` },
        last_changed: "",
        last_updated: "",
      };
      entities[cameraId] = { entity_id: cameraId, device_id: device, platform: "zoneminder", translation_key: null };
      entities[motionId] = { entity_id: motionId, device_id: device, platform: "zoneminder", translation_key: "motion" };
      windows[cameraId] = eventsFor(camera, frames[camera.id], now, random);
    }
    const fake = Object.assign(Object.create(Object.getPrototypeOf(real)), real, {
      states,
      entities,
      // Only the events command answers. Anything else, such as starting a
      // live stream, never resolves, so the frame stays on the still image.
      callWS: (message) =>
        message.type === "zoneminder/events"
          ? Promise.resolve(windows[message.entity_id])
          : new Promise(() => {}),
      callService: () => Promise.resolve(),
    });

    // Cover the view's own cards with a panel holding the demo card.
    const view = deep("hui-view-container")[0] ?? deep("hui-view")[0];
    const rect = view.getBoundingClientRect();
    const panel = document.createElement("div");
    panel.id = "zm-readme-panel";
    Object.assign(panel.style, {
      position: "fixed",
      left: `${rect.left}px`,
      top: `${rect.top}px`,
      right: "0",
      bottom: "0",
      padding: "12px",
      background: "var(--primary-background-color)",
      zIndex: "5",
      overflow: "hidden",
    });
    const card = document.createElement("zoneminder-card");
    card.setConfig({ type: "custom:zoneminder-card", columns: 2, entities: Object.keys(windows) });
    card.hass = fake;
    card.style.display = "block";
    card.style.maxWidth = `${width}px`;
    panel.append(card);
    document.body.append(panel);
    window.__zmReadme = { card, windows };
    return card;
  }

  /** Every tile has its still image and its strip drawn. */
  function cardReady() {
    const state = window.__zmReadme;
    if (!state) return false;
    const tiles = deep("zm-camera-tile", state.card.shadowRoot);
    return (
      tiles.length === CAMERAS.length &&
      tiles.every((tile) => {
        const still = tile.shadowRoot?.querySelector("img.still");
        return still?.complete && still.naturalWidth > 0 && tile.shadowRoot.querySelector(".strip svg rect");
      })
    );
  }

  /** Show a camera's hover preview over a motion event about `hoursAgo` back. */
  function hoverMotion(cameraId, hoursAgo) {
    const { card, windows } = window.__zmReadme;
    const tile = deep("zm-camera-tile", card.shadowRoot).find((t) => t.entity === `camera.${cameraId}`);
    const strip = tile.shadowRoot.querySelector(".strip");
    const rect = strip.getBoundingClientRect();
    const window_ = windows[`camera.${cameraId}`];
    const start = Date.parse(window_.start);
    const end = Date.parse(window_.end);
    const target = Date.now() - hoursAgo * HOUR;
    const motion = window_.events
      .filter((e) => e.alarm_frames > 0 && !e.in_progress)
      .sort((a, b) => Math.abs(Date.parse(a.start) - target) - Math.abs(Date.parse(b.start) - target))[0];
    const middle = Date.parse(motion.start) + motion.length * 500;
    strip.dispatchEvent(
      new PointerEvent("pointermove", {
        clientX: rect.left + ((middle - start) / (end - start)) * rect.width,
        clientY: rect.top + rect.height / 2,
        bubbles: true,
        composed: true,
      }),
    );
  }

  /** The first ZoneMinder camera that isn't rotated, with its device. */
  function landscapeCamera() {
    const h = hass();
    const camera = Object.values(h.entities).find(
      (e) =>
        e.platform === "zoneminder" &&
        e.entity_id.startsWith("camera.") &&
        !Number(h.states[e.entity_id]?.attributes.orientation_degrees),
    );
    if (!camera) return null;
    const device = h.devices[camera.device_id];
    return { deviceId: camera.device_id, name: device.name_by_user || device.name };
  }

  /**
   * Keep replacing text and camera pictures on the page, for pages that
   * would otherwise show a real name, address or frame. `replacements` is a
   * list of [from, to] strings; `picture` replaces camera images.
   */
  function scrub(replacements, picture) {
    const apply = (text) => replacements.reduce((value, [from, to]) => value.split(from).join(to), text);
    const run = () => {
      const stack = [document];
      while (stack.length) {
        const root = stack.pop();
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          const value = apply(node.nodeValue);
          if (value !== node.nodeValue) node.nodeValue = value;
        }
        root.querySelectorAll("*").forEach((el) => {
          if (el.shadowRoot) stack.push(el.shadowRoot);
          for (const attribute of ["title", "aria-label", "label", "alt"]) {
            const value = el.getAttribute(attribute);
            if (value && apply(value) !== value) el.setAttribute(attribute, apply(value));
          }
          if (el.tagName === "IMG" && /camera_proxy|image_proxy|api\/zoneminder/.test(el.src)) el.src = picture;
          if (el.tagName === "VIDEO") el.style.visibility = "hidden";
        });
      }
    };
    run();
    clearInterval(window.__zmScrub);
    window.__zmScrub = setInterval(run, 200);
  }

  /** The page's ha-card elements whose heading matches, in page coordinates. */
  function cardRects(headings) {
    return deep("ha-card")
      .map((card) => {
        const heading = (
          card.getAttribute("header") ||
          card.querySelector("h1, .card-header")?.textContent ||
          card.shadowRoot?.querySelector("h1, .card-header")?.textContent ||
          ""
        ).trim();
        return { card, heading };
      })
      .filter(({ heading }) => headings.some((h) => heading.startsWith(h)));
  }

  /** Hide device-page cards other than the ones shown, so none peek in. */
  function hideCardsExcept(headings) {
    for (const card of deep("ha-card")) {
      const keep = cardRects(headings).some((match) => match.card === card);
      if (!keep && card.getBoundingClientRect().width > 100) card.style.visibility = "hidden";
    }
  }

  /** Bounding box around the named cards, padded, in CSS pixels. */
  function boxAround(headings, pad = 8) {
    const rects = cardRects(headings).map(({ card }) => card.getBoundingClientRect());
    const left = Math.min(...rects.map((r) => r.left)) - pad;
    const top = Math.min(...rects.map((r) => r.top)) - pad;
    const right = Math.max(...rects.map((r) => r.right)) + pad;
    const bottom = Math.max(...rects.map((r) => r.bottom)) + pad;
    return { x: left, y: top, width: right - left, height: bottom - top };
  }

  /** The config-flow dialog's visible surface. */
  function dialogBox() {
    const surface = deep(".mdc-dialog__surface, ha-dialog-header")
      .map((el) => el.closest?.(".mdc-dialog__surface") ?? el)
      .concat(deep("dialog[open], .dialog, wa-dialog, ha-wa-dialog"))
      .map((el) => el.getBoundingClientRect())
      .filter((r) => r.width > 300 && r.height > 200)
      .sort((a, b) => a.width * a.height - b.width * b.height)[0];
    return surface ? { x: surface.left, y: surface.top, width: surface.width, height: surface.height } : null;
  }

  window.zmReadme = {
    deep,
    mountCard,
    cardReady,
    hoverMotion,
    landscapeCamera,
    scrub,
    hideCardsExcept,
    boxAround,
    dialogBox,
  };
})();
