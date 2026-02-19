/**
 * WhatsApp Web bridge for OctopusOS CommunicationOS.
 *
 * Transport:
 * - stdin: JSON lines (commands)
 * - stdout: JSON lines (events)
 *
 * Events:
 * - {type:"status", state:"starting"|"needs_qr"|"ready"|"auth_failure"|"disconnected", detail?:string}
 * - {type:"qr", qr:string, qr_data_url:string, ts_ms:number}
 * - {type:"ready", ts_ms:number}
 * - {type:"inbound_message", message_id:string, from:string, to?:string, body?:string, ts_ms:number, is_group:boolean}
 *
 * Commands:
 * - {cmd:"send", to:string, text:string}
 * - {cmd:"status"}
 * - {cmd:"shutdown"}
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import readline from "node:readline";

import qrcode from "qrcode";
import pkg from "whatsapp-web.js";

const { Client, LocalAuth } = pkg;

function nowMs() {
  return Date.now();
}

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

function pickChromeExecutable(explicitPath) {
  const raw = (explicitPath || "").trim();
  if (raw) return raw;

  // macOS common Chrome paths
  const macCandidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ];
  for (const p of macCandidates) {
    try {
      if (fs.existsSync(p)) return p;
    } catch {}
  }

  // Linux/Windows: let puppeteer pick default (may require bundled chromium).
  return "";
}

function ensureDir700(dir) {
  if (!dir) return;
  fs.mkdirSync(dir, { recursive: true });
  if (os.platform() !== "win32") {
    try {
      fs.chmodSync(dir, 0o700);
    } catch {}
  }
}

const stateDir = (process.env.OCTOPUSOS_WHATSAPP_STATE_DIR || "").trim();
const chromePath = pickChromeExecutable(process.env.OCTOPUSOS_WHATSAPP_CHROME_PATH);

if (!stateDir) {
  emit({ type: "status", state: "auth_failure", detail: "missing_state_dir_env", ts_ms: nowMs() });
  process.exit(2);
}

ensureDir700(stateDir);

emit({ type: "status", state: "starting", ts_ms: nowMs() });

let latestState = "starting";
let latestQr = null;
let latestQrDataUrl = null;

const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: stateDir,
  }),
  puppeteer: {
    headless: true,
    executablePath: chromePath || undefined,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
    ],
  },
});

client.on("qr", async (qr) => {
  latestState = "needs_qr";
  latestQr = qr;
  try {
    latestQrDataUrl = await qrcode.toDataURL(qr, { errorCorrectionLevel: "M", margin: 1, scale: 6 });
  } catch (e) {
    latestQrDataUrl = null;
  }
  emit({ type: "status", state: "needs_qr", ts_ms: nowMs() });
  emit({ type: "qr", qr, qr_data_url: latestQrDataUrl, ts_ms: nowMs() });
});

client.on("authenticated", () => {
  emit({ type: "status", state: "authenticated", ts_ms: nowMs() });
});

client.on("ready", () => {
  latestState = "ready";
  emit({ type: "ready", ts_ms: nowMs() });
  emit({ type: "status", state: "ready", ts_ms: nowMs() });
});

client.on("auth_failure", (msg) => {
  latestState = "auth_failure";
  emit({ type: "status", state: "auth_failure", detail: String(msg || ""), ts_ms: nowMs() });
});

client.on("disconnected", (reason) => {
  latestState = "disconnected";
  emit({ type: "status", state: "disconnected", detail: String(reason || ""), ts_ms: nowMs() });
});

client.on("message", (message) => {
  try {
    // message.from is chat id like '1234567890@c.us' or group '...@g.us'
    const from = String(message.from || "");
    const to = String(message.to || "");
    const body = typeof message.body === "string" ? message.body : "";
    const isGroup = from.endsWith("@g.us");
    const fromMe = Boolean(message.fromMe);
    const messageId = message?.id?._serialized ? String(message.id._serialized) : `wa_${nowMs()}`;
    emit({
      type: "inbound_message",
      message_id: messageId,
      from,
      to,
      body,
      from_me: fromMe,
      ts_ms: nowMs(),
      is_group: isGroup,
    });
  } catch (e) {
    emit({ type: "status", state: "error", detail: `inbound_parse:${String(e)}`, ts_ms: nowMs() });
  }
});

async function doSend(to, text) {
  const target = String(to || "").trim();
  const msg = String(text || "");
  if (!target) throw new Error("missing_to");
  if (!msg) throw new Error("missing_text");
  await client.sendMessage(target, msg);
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on("line", async (line) => {
  const raw = String(line || "").trim();
  if (!raw) return;
  let cmd;
  try {
    cmd = JSON.parse(raw);
  } catch {
    emit({ type: "status", state: "error", detail: "invalid_json_command", ts_ms: nowMs() });
    return;
  }

  const c = String(cmd.cmd || "").trim();
  if (c === "status") {
    emit({
      type: "status",
      state: latestState,
      ts_ms: nowMs(),
      has_qr: Boolean(latestQr),
    });
    return;
  }
  if (c === "send") {
    try {
      await doSend(cmd.to, cmd.text);
      emit({ type: "send_result", ok: true, ts_ms: nowMs() });
    } catch (e) {
      emit({ type: "send_result", ok: false, error: String(e), ts_ms: nowMs() });
    }
    return;
  }
  if (c === "shutdown") {
    emit({ type: "status", state: "shutting_down", ts_ms: nowMs() });
    try {
      await client.destroy();
    } catch {}
    process.exit(0);
  }

  emit({ type: "status", state: "error", detail: `unknown_cmd:${c}`, ts_ms: nowMs() });
});

process.on("SIGINT", async () => {
  try {
    await client.destroy();
  } catch {}
  process.exit(0);
});

process.on("SIGTERM", async () => {
  try {
    await client.destroy();
  } catch {}
  process.exit(0);
});

// Start client (async)
client.initialize().catch((e) => {
  latestState = "auth_failure";
  emit({ type: "status", state: "auth_failure", detail: `init_failed:${String(e)}`, ts_ms: nowMs() });
  process.exit(3);
});
