/* Minimal H5 client for M3 device binding.
 *
 * Flow:
 * - Scan / input pairing code (from WebUI).
 * - POST /api/devices/pair -> returns request_id + poll_secret.
 * - Poll /api/devices/pair/{id}/status?poll_secret=... until approved; receive token once.
 * - Chat via /api/mobile/chat with Authorization: Device <token>
 */

const LS = {
  requestId: 'octopusos_device_request_id',
  pollSecret: 'octopusos_device_poll_secret',
  token: 'octopusos_device_token',
  fingerprint: 'octopusos_device_fingerprint',
}

function $(id) {
  return document.getElementById(id)
}

function setStatus(text) {
  $('status').textContent = text
}

function deviceFingerprint() {
  let fp = localStorage.getItem(LS.fingerprint)
  if (fp) return fp
  // Stable-but-not-sensitive fingerprint: random seed stored on device.
  fp = 'fp_' + Math.random().toString(36).slice(2) + '_' + Date.now().toString(36)
  localStorage.setItem(LS.fingerprint, fp)
  return fp
}

function addMsg(role, text) {
  const el = document.createElement('div')
  el.className = 'msg ' + role
  el.textContent = text
  $('messages').appendChild(el)
  $('messages').scrollTop = $('messages').scrollHeight
}

async function api(method, path, body, headers) {
  const opts = { method, headers: Object.assign({ 'Content-Type': 'application/json' }, headers || {}) }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const resp = await fetch(path, opts)
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    const msg = (data && (data.detail || data.error)) || resp.statusText
    throw new Error(`${resp.status}: ${msg}`)
  }
  return data
}

async function pairWithCode(code) {
  const payload = {
    pairing_code: String(code || '').trim(),
    device_fingerprint: deviceFingerprint(),
    device_name: navigator.userAgent.slice(0, 80),
  }
  const data = await api('POST', '/api/devices/pair', payload)
  const requestId = data?.request?.id
  const pollSecret = data?.poll_secret
  if (!requestId || !pollSecret) throw new Error('pair_failed')
  localStorage.setItem(LS.requestId, requestId)
  localStorage.setItem(LS.pollSecret, pollSecret)
  setStatus('Pending approval')
  $('chat').classList.add('hidden')
  $('pairing').classList.remove('hidden')
  await pollUntilApproved()
}

async function pollOnce() {
  const requestId = localStorage.getItem(LS.requestId)
  const pollSecret = localStorage.getItem(LS.pollSecret)
  if (!requestId || !pollSecret) return { status: 'unpaired' }
  return api('GET', `/api/devices/pair/${encodeURIComponent(requestId)}/status?poll_secret=${encodeURIComponent(pollSecret)}`)
}

async function pollUntilApproved() {
  for (let i = 0; i < 120; i++) {
    const st = await pollOnce().catch(() => null)
    if (!st) {
      await new Promise((r) => setTimeout(r, 1000))
      continue
    }
    const status = st.status
    if (status === 'approved') {
      if (st.credential && st.credential.token) {
        localStorage.setItem(LS.token, st.credential.token)
      }
      setStatus('Connected')
      $('pairing').classList.add('hidden')
      $('chat').classList.remove('hidden')
      return
    }
    if (status === 'rejected' || status === 'revoked') {
      setStatus('Rejected/Revoked')
      return
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  setStatus('Timeout waiting approval')
}

async function sendChat(text) {
  const token = localStorage.getItem(LS.token)
  if (!token) throw new Error('missing_token')
  const payload = { text: String(text || '') }
  const data = await api('POST', '/api/mobile/chat', payload, { Authorization: `Device ${token}` })
  return data
}

// Scanner (best effort): BarcodeDetector is not universally available.
let stream = null
let scanLoop = null

async function startScan() {
  $('scanArea').classList.remove('hidden')
  $('manualArea').classList.add('hidden')
  $('scanHint').textContent = ''
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    $('scanHint').textContent = 'Camera not available. Use Enter Code.'
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
    $('video').srcObject = stream
    await $('video').play()
  } catch (e) {
    $('scanHint').textContent = 'Camera permission denied. Use Enter Code.'
    return
  }

  if (!('BarcodeDetector' in window)) {
    $('scanHint').textContent = 'BarcodeDetector unsupported. Use Enter Code.'
    return
  }
  const detector = new window.BarcodeDetector({ formats: ['qr_code'] })
  const canvas = $('canvas')
  const ctx = canvas.getContext('2d')

  scanLoop = setInterval(async () => {
    try {
      const v = $('video')
      if (!v.videoWidth || !v.videoHeight) return
      canvas.width = v.videoWidth
      canvas.height = v.videoHeight
      ctx.drawImage(v, 0, 0, canvas.width, canvas.height)
      const bitmap = await createImageBitmap(canvas)
      const codes = await detector.detect(bitmap)
      if (codes && codes.length) {
        const code = codes[0].rawValue
        stopScan()
        await pairWithCode(code)
      }
    } catch (_) {
      // ignore
    }
  }, 400)
}

function stopScan() {
  if (scanLoop) clearInterval(scanLoop)
  scanLoop = null
  if (stream) {
    try {
      stream.getTracks().forEach((t) => t.stop())
    } catch (_) {}
  }
  stream = null
  $('scanArea').classList.add('hidden')
}

function showManual() {
  stopScan()
  $('manualArea').classList.remove('hidden')
  $('codeInput').focus()
}

function forgetToken() {
  localStorage.removeItem(LS.token)
  localStorage.removeItem(LS.requestId)
  localStorage.removeItem(LS.pollSecret)
  setStatus('Unpaired')
  $('chat').classList.add('hidden')
  $('pairing').classList.remove('hidden')
}

// Wiring
$('btnStartScan').addEventListener('click', () => void startScan())
$('btnStopScan').addEventListener('click', () => stopScan())
$('btnUseCode').addEventListener('click', () => showManual())
$('btnSubmitCode').addEventListener('click', () => void pairWithCode($('codeInput').value))
$('btnDisconnect').addEventListener('click', () => forgetToken())
$('btnSend').addEventListener('click', async () => {
  const text = $('chatInput').value.trim()
  if (!text) return
  $('chatInput').value = ''
  addMsg('user', text)
  try {
    const data = await sendChat(text)
    addMsg('assistant', data.reply || '')
  } catch (e) {
    addMsg('assistant', String(e.message || e))
  }
})

window.addEventListener('load', async () => {
  const token = localStorage.getItem(LS.token)
  if (token) {
    setStatus('Connected')
    $('pairing').classList.add('hidden')
    $('chat').classList.remove('hidden')
    return
  }
  const requestId = localStorage.getItem(LS.requestId)
  const pollSecret = localStorage.getItem(LS.pollSecret)
  if (requestId && pollSecret) {
    setStatus('Pending approval')
    await pollUntilApproved()
  } else {
    setStatus('Unpaired')
  }
})

