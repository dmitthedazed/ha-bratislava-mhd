/*
 * Bratislava MHD card: one card per stop, live departures of its platforms.
 *
 *   type: custom:bratislava-mhd-card
 *   entities: [sensor.x, ...]   # optional, defaults to every Bratislava MHD sensor
 *   stop: 394                   # one stop (as the card editor sets it), or
 *   stops: [394, 274]           # several stops, one card each; omit both for every stop
 *   platforms: ["A", "B"]       # optional, only these platforms
 * Tapping a platform chip in the header shows only that platform; tapping it again shows all.
 *   max: 6                      # departures per stop
 *   show_vehicle: true          # vehicle model, low floor, A/C
 */

// Line colours, badge shapes and vehicle icons follow Transi (https://github.com/magicsk/Transi, GPL-3.0),
// util/LineColor.kt and util/UtilFuns.kt customizeLineText; the icons are Material Design icons (Apache-2.0).
const LINE_BG = {"1": "#EC691F", "3": "#E31E24", "4": "#5171B9", "14": "#5171B9", "80": "#DB821A", "99": "#EB609D", "7": "#FFED03", "8": "#4D897C", "9": "#889923", "21": "#338632", "33": "#7468AC", "37": "#E31E24", "40": "#E51A4B", "42": "#A65430", "44": "#B84A94", "47": "#AF8E13", "49": "#D36D1E", "50": "#075369", "60": "#2B4493", "61": "#A21517", "63": "#642F6C", "88": "#642F6C", "64": "#0E562C", "68": "#897917", "71": "#047DB3", "72": "#899D1C", "83": "#0E7BBA", "84": "#0E7BBA", "93": "#AB075F", "94": "#AB075F", "95": "#EC6A1F", "96": "#3FA03B", "98": "#B45C2E", "570": "#AAD29B", "245": "#BCB5DA", "255": "#ACD086", "637": "#ACD086", "256": "#EA5558", "257": "#6CADDF", "258": "#9D9E9E", "269": "#A2D9F7", "523": "#EA544A", "636": "#EA544A", "525": "#AF9778", "527": "#AF9778", "540": "#78B833", "550": "#78B833", "610": "#D4A31D", "620": "#F6BFD9", "632": "#EED502", "720": "#FABC48", "740": "#FABC48", "737": "#EA533D", "298": "#000000", "299": "#000000", "598": "#000000", "599": "#000000", "699": "#000000", "798": "#000000", "799": "#000000"};
const LINE_FG = {"7": "#000000", "N21": "#54C279", "N29": "#BBC79A", "N31": "#DDF8DE", "N33": "#B1A4E1", "N34": "#78B1DC", "N37": "#FFA5B4", "N44": "#D780C8", "N47": "#FCC802", "N53": "#82D7DF", "N55": "#FADF17", "N56": "#C1EA8B", "N61": "#FB7373", "N70": "#FFD8A8", "N72": "#BBD702", "N74": "#B5F1BB", "N80": "#FEAE46", "N91": "#FFF4B3", "N93": "#E43692", "N95": "#EE6901", "N99": "#F6B4D5", "298": "#FFFFFF", "299": "#FFFFFF", "598": "#FFFFFF", "599": "#FFFFFF", "699": "#FFFFFF", "798": "#FFFFFF", "799": "#FFFFFF"};
const LINE_FALLBACK = {"train": "#166DD4", "AT_train": "#FF671F", "night": "#2B2A29", "replacement": "#EF7F1A", "regio": "#BFBFB9", "ldefault": "#52595C", "white": "#FFFFFF", "black": "#000000"};

const isTrain = (line) => /^(S|R|AT)/.test(line);
const lineNumber = (line) => (/^\d+$/.test(line) ? Number(line) : NaN);

function lineBg(line) {
  if (LINE_BG[line]) return LINE_BG[line];
  if (/^(S|R)/.test(line)) return LINE_FALLBACK.train;
  if (line.startsWith("AT")) return LINE_FALLBACK.AT_train;
  if (line.startsWith("N")) return LINE_FALLBACK.night;
  if (line.startsWith("X")) return LINE_FALLBACK.replacement;
  if (lineNumber(line) > 200) return LINE_FALLBACK.regio;
  return LINE_FALLBACK.ldefault;
}

function lineFg(line) {
  if (LINE_FG[line]) return LINE_FG[line];
  return line.startsWith("X") || lineNumber(line) > 200 ? "#000000" : "#FFFFFF";
}

// Capsule below line 20 and for trains, 4px rounded rectangle otherwise.
const lineShape = (line) => ((lineNumber(line) || 99) < 20 || isTrain(line) ? "capsule" : "rect");

function vehicleKind(line) {
  if (isTrain(line)) return "train";
  if ((lineNumber(line) || 99) < 20) return "tram";
  if (lineNumber(line) > 200) return "regiobus";
  return "bus";
}

const BUS_PATH = "M4,16c0,0.88 0.39,1.67 1,2.22L5,20c0,0.55 0.45,1 1,1h1c0.55,0 1,-0.45 1,-1v-1h8v1c0,0.55 0.45,1 1,1h1c0.55,0 1,-0.45 1,-1v-1.78c0.61,-0.55 1,-1.34 1,-2.22L20,6c0,-3.5 -3.58,-4 -8,-4s-8,0.5 -8,4v10zM7.5,17c-0.83,0 -1.5,-0.67 -1.5,-1.5S6.67,14 7.5,14s1.5,0.67 1.5,1.5S8.33,17 7.5,17zM16.5,17c-0.83,0 -1.5,-0.67 -1.5,-1.5s0.67,-1.5 1.5,-1.5 1.5,0.67 1.5,1.5 -0.67,1.5 -1.5,1.5zM18,11L6,11L6,6h12v5z";
const VEHICLE_PATHS = {
  bus: BUS_PATH,
  regiobus: BUS_PATH,
  tram: "M19,16.94V8.5c0,-2.79 -2.61,-3.4 -6.01,-3.49l0.76,-1.51H17V2H7v1.5h4.75l-0.76,1.52C7.86,5.11 5,5.73 5,8.5v8.44c0,1.45 1.19,2.66 2.59,2.97L6,21.5v0.5h2.23l2,-2H14l2,2h2v-0.5L16.5,20h-0.08c1.69,0 2.58,-1.37 2.58,-3.06zM12,18.5c-0.83,0 -1.5,-0.67 -1.5,-1.5s0.67,-1.5 1.5,-1.5 1.5,0.67 1.5,1.5 -0.67,1.5 -1.5,1.5zM17,14H7V9h10v5z",
  train: "M12,2c-4,0 -8,0.5 -8,4v9.5C4,17.43 5.57,19 7.5,19L6,20.5v0.5h2.23l2,-2L14,19l2,2h2v-0.5L16.5,19c1.93,0 3.5,-1.57 3.5,-3.5L20,6c0,-3.5 -3.58,-4 -8,-4zM7.5,17c-0.83,0 -1.5,-0.67 -1.5,-1.5S6.67,14 7.5,14s1.5,0.67 1.5,1.5S8.33,17 7.5,17zM11,10L6,10L6,6h5v4zM13,10L13,6h5v4h-5zM16.5,17c-0.83,0 -1.5,-0.67 -1.5,-1.5s0.67,-1.5 1.5,-1.5 1.5,0.67 1.5,1.5 -0.67,1.5 -1.5,1.5z",
};
// Transi stopTypeIcon tints: city bus red, regional bus amber, train blue.
const STOP_TINT = { bus: "#FC3737", regio_bus: "#FFC107", train: "#4184F2" };
const STOP_KIND = { regio_bus: "regiobus", train: "train" };

const icon = (kind, cls) =>
  `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="${VEHICLE_PATHS[kind] || BUS_PATH}"/></svg>`;

const I18N = {
  en: { now: "now", min: "min", empty: "No departures soon", offline: "Reconnecting…", plan: "timetable", late: "late", early: "early" },
  ru: { now: "сейчас", min: "мин", empty: "Ближайших отправлений нет", offline: "Переподключение…", plan: "по расписанию", late: "опозд.", early: "раньше" },
  uk: { now: "зараз", min: "хв", empty: "Найближчих відправлень немає", offline: "Перепідключення…", plan: "за розкладом", late: "запізн.", early: "раніше" },
  sk: { now: "teraz", min: "min", empty: "Žiadne blízke odchody", offline: "Pripájam…", plan: "podľa CP", late: "mešká", early: "skôr" },
};

// Bratislava timetables use the 24-hour clock whatever the UI language.
const clockTime = (epoch) =>
  new Date(epoch * 1000).toLocaleTimeString("sk-SK", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class BratislavaMhdCard extends HTMLElement {
  setConfig(config) {
    this._config = { max: 6, show_vehicle: true, ...config };
    // Platform shown alone, by stop id; set by tapping its chip.
    this._only = new Map();
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => {
        const chip = ev.target.closest("[data-plat]");
        if (!chip) return;
        const stop = Number(chip.dataset.stop);
        const plat = chip.dataset.plat;
        if (this._only.get(stop) === plat) this._only.delete(stop);
        else this._only.set(stop, plat);
        this._render();
      });
    }
    this._render();
  }

  set hass(hass) {
    const prev = this._hass;
    this._hass = hass;
    const ids = this._entityIds();
    if (!prev || ids.some((id) => prev.states[id] !== hass.states[id]) || ids.length !== this._lastCount) {
      this._lastCount = ids.length;
      this._render();
    }
  }

  connectedCallback() {
    this._timer = setInterval(() => this._render(), 1000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  getCardSize() {
    return 2 + (this._config?.max ?? 6);
  }

  static getStubConfig(hass) {
    // A new card shows one stop: the first configured one.
    const first = Object.values(hass?.states || {}).find((st) => st.attributes.mhd_board);
    return first ? { stop: first.attributes.stop_id, max: 6 } : { max: 6 };
  }

  static getConfigElement() {
    return document.createElement("bratislava-mhd-card-editor");
  }

  get _lang() {
    return this._hass?.locale?.language || this._hass?.language || "en";
  }

  get _t() {
    return I18N[this._lang.slice(0, 2)] || I18N.en;
  }

  _entityIds() {
    if (!this._hass) return [];
    const ids = this._config.entities?.length
      ? this._config.entities
      : Object.keys(this._hass.states).filter((id) => id.startsWith("sensor.") && this._hass.states[id].attributes.mhd_board);
    const stops = this._config.stop != null ? [Number(this._config.stop)] : this._config.stops?.map(Number);
    const platforms = this._config.platforms?.length ? this._config.platforms.map(String) : null;
    return ids.filter((id) => {
      const s = this._hass.states[id];
      return (
        s &&
        (!stops || stops.includes(Number(s.attributes.stop_id))) &&
        (!platforms || platforms.includes(String(s.attributes.platform)))
      );
    });
  }

  _stops() {
    const byStop = new Map();
    for (const id of this._entityIds()) {
      const a = this._hass.states[id].attributes;
      if (!byStop.has(a.stop_id)) {
        byStop.set(a.stop_id, { id: a.stop_id, name: a.stop_name, type: a.stop_type, connected: false, departures: [], info: a.info || [], platforms: [] });
      }
      const stop = byStop.get(a.stop_id);
      stop.connected ||= a.connected;
      stop.platforms.push(String(a.platform));
      const only = this._only?.get(Number(a.stop_id));
      if (only && only !== String(a.platform)) continue;
      for (const d of a.departures || []) stop.departures.push({ ...d, platform: only ? null : a.platform });
    }
    const now = Date.now() / 1000;
    for (const stop of byStop.values()) {
      stop.departures = stop.departures
        .filter((d) => d.expected >= now - 30)
        .sort((x, y) => x.expected - y.expected)
        .slice(0, this._config.max);
      stop.platforms.sort((x, y) => x.localeCompare(y, "sk", { numeric: true }));
    }
    return [...byStop.values()];
  }

  _countdown(d) {
    const secs = d.expected - Date.now() / 1000;
    if (secs <= 30) return { big: this._t.now, small: "", soon: true };
    const mins = Math.floor(secs / 60);
    if (mins >= 60) {
      // Clock time an hour or more out.
      return { big: clockTime(d.expected), small: "", soon: false, clock: true };
    }
    return { big: mins < 1 ? "<1" : String(mins), small: this._t.min, soon: mins <= 2 };
  }

  _row(d) {
    const c = this._countdown(d);
    const clock = clockTime(d.expected);
    let delay = "";
    if (d.realtime && d.delay > 0) delay = `<span class="delay late">+${esc(d.delay)} ${this._t.min}</span>`;
    else if (d.realtime && d.delay < 0) delay = `<span class="delay early">${esc(d.delay)} ${this._t.min}</span>`;
    const v = this._config.show_vehicle && d.vehicle;
    const vehicle = v
      ? `<span class="veh">${esc(v.type)}${v.low_floor ? ' <ha-icon icon="mdi:wheelchair-accessibility"></ha-icon>' : ""}${v.ac ? ' <ha-icon icon="mdi:snowflake"></ha-icon>' : ""}</span>`
      : "";
    const where = d.last_stop ? `<span class="where"><ha-icon icon="mdi:map-marker-path"></ha-icon>${esc(d.last_stop)}</span>` : "";
    return `
      <div class="row ${c.soon ? "soon" : ""} ${d.stuck ? "stuck" : ""}">
        ${icon(vehicleKind(d.line), "veh-icon")}
        <div class="lcell">
          <span class="line ${lineShape(d.line)} ${/^\d$/.test(d.line) ? "one" : ""}"
                style="background:${lineBg(d.line)};color:${lineFg(d.line)}">${esc(d.line)}</span>
        </div>
        <div class="main">
          <div class="head" lang="sk">${esc(d.headsign)}</div>
          <div class="meta">
            ${d.platform ? `<span class="plat">${esc(d.platform)}</span>` : ""}
            <span class="clock">${clock}</span>
            ${delay}
            ${d.realtime ? '<span class="live" title="live"></span>' : `<span class="plan">${this._t.plan}</span>`}
            ${where}
            ${vehicle}
          </div>
        </div>
        <div class="time ${d.realtime ? "" : "approx"}">
          <span class="big ${c.clock ? "at" : ""}">${esc(c.big)}</span><span class="small">${esc(c.small)}</span>
        </div>
      </div>`;
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const stops = this._stops();
    const cards = stops.map((s) => `
      <ha-card>
        <div class="header">
          <span class="stop-icon" style="color:${STOP_TINT[s.type] || STOP_TINT.bus}">${icon(STOP_KIND[s.type] || "bus", "")}</span>
          <div class="title">${esc(this._config.title || s.name)}</div>
          <div class="plats">${s.platforms.length > 1 ? s.platforms.map((p) => {
            const only = this._only.get(Number(s.id));
            const cls = only === p ? "active" : only ? "dim" : "";
            return `<button class="plat chip ${cls}" data-stop="${esc(s.id)}" data-plat="${esc(p)}">${esc(p)}</button>`;
          }).join("") : s.platforms.map((p) => `<span class="plat chip">${esc(p)}</span>`).join("")}</div>
          <span class="conn ${s.connected ? "on" : "off"}" title="${s.connected ? "online" : this._t.offline}"></span>
        </div>
        ${s.info.length ? `<div class="info">${s.info.map(esc).join("<br>")}</div>` : ""}
        <div class="rows">
          ${s.departures.length ? s.departures.map((d) => this._row(d)).join("") : `<div class="empty">${s.connected ? this._t.empty : this._t.offline}</div>`}
        </div>
      </ha-card>`).join("");
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><div class="stack">${cards || `<ha-card><div class="empty">Bratislava MHD: no sensors</div></ha-card>`}</div>`;
  }
}

const STYLE = `
  .stack { display: flex; flex-direction: column; gap: var(--grid-card-gap, 8px); }
  /* Layout follows the card's own width (sections grid, columns, phones), not the screen's. */
  ha-card { overflow: hidden; container-type: inline-size; }
  .header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 12px 16px; }
  .stop-icon svg { width: 24px; height: 24px; display: block; }
  /* The name keeps its room; platform chips wrap to their own line when they don't fit beside it. */
  .title { font-size: 1.15em; font-weight: 600; flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .plats { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; flex: 0 0 auto; max-width: 100%; margin-left: auto; order: 1; }
  .conn { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .conn.on { background: var(--success-color, #43a047); }
  .conn.off { background: var(--warning-color, #ffa000); animation: blink 1.2s infinite; }
  .info { margin: 0 16px 12px; padding: 8px 10px; border-radius: 8px; font-size: .85em;
          background: color-mix(in srgb, var(--warning-color, #ffa000) 15%, transparent); }
  .rows { padding-bottom: 6px; border-top: 1px solid var(--divider-color); }
  /* Fixed columns so every headsign and countdown lines up: icon | line | text | time. */
  .row { position: relative; display: grid; grid-template-columns: 18px 44px minmax(0, 1fr) auto; column-gap: 10px;
         align-items: center; padding: 10px 16px; transition: background .3s; }
  .row + .row::before { content: ""; position: absolute; top: 0; left: 16px; right: 16px; border-top: 1px solid var(--divider-color); }
  .row.soon { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
  .row.soon::before, .row.soon + .row::before { display: none; }
  .row.stuck .head { text-decoration: line-through; opacity: .6; }
  .lcell { display: flex; justify-content: center; }
  .veh-icon { width: 18px; height: 18px; display: block; color: var(--secondary-text-color); opacity: .8; }
  /* Sized from the one-digit circle: 28px tall, never narrower than it is tall. */
  .line { display: inline-block; box-sizing: border-box; text-align: center;
          height: 28px; min-width: 28px; max-width: 44px; padding: 0 5px; overflow: hidden; white-space: nowrap;
          font-weight: 700; font-size: 15px; line-height: 28px; font-variant-numeric: tabular-nums;
          font-family: Roboto, var(--paper-font-common-base_-_font-family, sans-serif); }
  .line.capsule { border-radius: 14px; }
  .line.rect { border-radius: 4px; }
  .line.one { width: 28px; padding: 0; }
  .main { flex: 1; min-width: 0; }
  .head { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .meta { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; font-size: .8em; color: var(--secondary-text-color); margin-top: 3px; line-height: 1.4; }
  .meta ha-icon { --mdc-icon-size: 14px; }
  .plat { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 4px; box-sizing: border-box;
          border-radius: 4px; font-size: .85em; font-weight: 600; line-height: 1;
          background: color-mix(in srgb, var(--secondary-text-color) 15%, transparent); color: var(--primary-text-color); }
  .clock, .delay, .plan { white-space: nowrap; }
  .delay { font-weight: 600; }
  .delay.late { color: var(--error-color, #db4437); }
  .delay.early { color: var(--success-color, #43a047); }
  .live { width: 7px; height: 7px; border-radius: 50%; background: var(--success-color, #43a047); animation: pulse 2s infinite; }
  .plan { font-style: italic; }
  .where, .veh { display: inline-flex; align-items: center; gap: 2px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .time { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .time .big { font-size: 1.5em; font-weight: 700; }
  .time .small { font-size: .8em; margin-left: 2px; color: var(--secondary-text-color); }
  .time.approx .big::before { content: "~"; font-weight: 400; opacity: .6; }
  .row.soon .time .big { color: var(--primary-color); }
  .empty { padding: 20px 16px; text-align: center; color: var(--secondary-text-color); }
  .chip { font: inherit; font-size: .85em; font-weight: 600; line-height: 1; height: 24px; min-width: 24px; padding: 0 7px; border-radius: 999px;
          border: 1px solid var(--divider-color); background: none; color: var(--secondary-text-color); cursor: default; }
  button.chip { cursor: pointer; transition: background .2s, color .2s, opacity .2s; }
  button.chip:hover { border-color: var(--primary-color); }
  .chip.active { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
  .chip.dim { opacity: .5; }
  /* Narrow card: platforms under the name, no vehicle column, only the essentials in the detail line. */
  @container (max-width: 360px) {
    .header { padding: 12px; }
    .plats { order: 3; flex-basis: 100%; justify-content: flex-start; }
    .row { grid-template-columns: 40px minmax(0, 1fr) auto; column-gap: 8px; padding: 8px 12px; }
    .row + .row::before { left: 12px; right: 12px; }
    .veh-icon, .veh, .where, .plan { display: none; }
    .line { max-width: 40px; padding: 0 3px; font-size: 14px; }
    .head { white-space: normal; overflow-wrap: break-word; hyphens: auto; line-height: 1.25; }
    .time .big.at { font-size: 1.05em; }
    .meta { flex-wrap: nowrap; gap: 6px; overflow: hidden; }
    .meta > * { flex: none; }
    .time .big { font-size: 1.3em; }
    .info { margin: 0 12px 12px; }
  }
  /* Very narrow: drop the clock too, the countdown says it. */
  @container (max-width: 240px) {
    .clock { display: none; }
    .row { grid-template-columns: 34px minmax(0, 1fr) auto; column-gap: 6px; }
    .line { max-width: 34px; font-size: 13px; }
  }
  @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(67,160,71,.6); } 70% { box-shadow: 0 0 0 6px rgba(67,160,71,0); } 100% { box-shadow: 0 0 0 0 rgba(67,160,71,0); } }
  @keyframes blink { 50% { opacity: .3; } }
`;

customElements.define("bratislava-mhd-card", BratislavaMhdCard);

/** Visual editor: pick the stop, its platforms and how much to show. */
class BratislavaMhdCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _stops() {
    const stops = new Map();
    for (const st of Object.values(this._hass?.states || {})) {
      const a = st.attributes;
      if (!a.mhd_board) continue;
      if (!stops.has(a.stop_id)) stops.set(a.stop_id, { name: a.stop_name, platforms: [] });
      stops.get(a.stop_id).platforms.push(String(a.platform));
    }
    return stops;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const stops = this._stops();
    const stop = stops.get(Number(this._config.stop));
    const schema = [
      {
        name: "stop",
        selector: {
          select: { mode: "dropdown", options: [...stops].map(([id, s]) => ({ value: String(id), label: s.name })) },
        },
      },
      ...(stop
        ? [{ name: "platforms", selector: { select: { multiple: true, mode: "list", options: stop.platforms.sort() } } }]
        : []),
      { name: "max", selector: { number: { min: 1, max: 20, mode: "box" } } },
      { name: "show_vehicle", selector: { boolean: {} } },
      { name: "title", selector: { text: {} } },
    ];
    const labels = {
      stop: "Zastávka / Stop",
      platforms: "Nástupištia / Platforms (empty = all)",
      max: "Max departures",
      show_vehicle: "Vehicle info",
      title: "Title",
    };
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => labels[s.name] || s.name;
      this._form.addEventListener("value-changed", (ev) => {
        const value = { ...ev.detail.value };
        if (value.stop !== undefined) value.stop = Number(value.stop);
        // Platforms belong to the stop: drop them when it changes.
        if (value.stop !== this._config.stop) delete value.platforms;
        for (const k of ["platforms", "title"]) if (value[k] === "" || (Array.isArray(value[k]) && !value[k].length)) delete value[k];
        delete value.stops;
        this._config = { ...value, type: this._config.type };
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
        this._render();
      });
      this.append(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = schema;
    this._form.data = {
      show_vehicle: true,
      max: 6,
      ...this._config,
      stop: this._config.stop != null ? String(this._config.stop) : undefined,
    };
  }
}

customElements.define("bratislava-mhd-card-editor", BratislavaMhdCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "bratislava-mhd-card",
  name: "Bratislava MHD",
  description: "Live departures from the stops near you",
  preview: true,
});
