import './App.css'
import { useEffect, useRef, useState, useMemo } from 'react'
import { API_BASE } from './config'

async function apiFetch(url, options={}) {
  const opts = { credentials: 'include', ...options }
  return fetch(url, opts)
}

function TimerBox({ started, ended, elapsed }) {
  const [nowElapsed, setNowElapsed] = useState(elapsed)
  useEffect(() => {
    let id
    if (started && !ended) {
      id = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/timer`)
          const t = await res.json()
          setNowElapsed(t?.elapsed_seconds ?? null)
        } catch (err) {
          console.error('timer fetch failed', err)
        }
      }, 1000)
    }
    return () => { if (id) clearInterval(id) }
  }, [started, ended])

  const seconds = (ended ? elapsed : nowElapsed) ?? 0
  const hh = String(Math.floor(seconds / 3600)).padStart(2, '0')
  const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
  const ss = String(Math.floor(seconds % 60)).padStart(2, '0')

  return (
    <div className="mt-3 text-sm">
      <div className="text-2xl font-mono tracking-wider">{hh}:{mm}:{ss}</div>
      <div className="text-xs text-gray-500 mt-1">
        {started ? (ended ? 'Completed' : 'Running...') : 'Not started'}
      </div>
    </div>
  )
}

function Badge({ color = 'sky', children }) {
  const map = {
    sky: 'bg-sky-100 text-sky-700 border-sky-200',
    green: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    red: 'bg-rose-100 text-rose-700 border-rose-200',
    gray: 'bg-gray-100 text-gray-700 border-gray-200',
    amber: 'bg-amber-100 text-amber-800 border-amber-200',
  }
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${map[color] || map.gray}`}>
      {children}
    </span>
  )
}

function Field({ label, children, hint }) {
  return (
    <label className="text-sm">
      <div className="flex items-center gap-2">
        <span className="font-medium text-gray-800">{label}</span>
        {hint && <span className="text-xs text-gray-500">{hint}</span>}
      </div>
      <div className="mt-1">{children}</div>
    </label>
  )
}

function Navbar({ onLogout }) {
  return (
    <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded bg-sky-500" />
          <span className="font-semibold">TTD Bot</span>
        </div>
        <nav className="hidden sm:flex items-center gap-6 text-sm">
          <a href="#dashboard" className="hover:text-sky-600">Dashboard</a>
          <a href="#config" className="hover:text-sky-600">Configuration</a>
          <a href="#logs" className="hover:text-sky-600">Logs</a>
          <button onClick={onLogout} className="text-xs rounded border px-2 py-1 hover:bg-gray-50">Logout</button>
        </nav>
      </div>
    </header>
  )
}

function Hero() {
  const [imgUrl, setImgUrl] = useState('')
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function refresh() {
    setLoading(true); setError('')
    try {
      const u = `${API_BASE}/screenshot?t=${Date.now()}`
      // Optimistically set image URL (browser will request it directly)
      setImgUrl(u)
      const res2 = await apiFetch(`${API_BASE}/current-url`)
      const data2 = await res2.json()
      setUrl(data2?.url || '')
    } catch {
      setError('Preview unavailable')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Auto refresh when page opens
    refresh()
    const id = setInterval(refresh, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <section className="bg-gradient-to-b from-white to-sky-50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
              TTD Srivari Seva Booking Assistant
            </h1>
            <p className="mt-4 text-base sm:text-lg text-gray-600">
              Manage members, track booking logs, and control the bot from a responsive web UI.
            </p>
            <div className="mt-6 flex flex-col sm:flex-row gap-3">
              <a href="#dashboard" className="inline-flex items-center justify-center rounded-md bg-sky-600 px-4 py-2 text-white hover:bg-sky-700">
                Open Dashboard
              </a>
              <a href="#config" className="inline-flex items-center justify-center rounded-md border px-4 py-2 hover:bg-gray-50">
                Edit Configuration
              </a>
            </div>
            <div className="mt-4 text-xs text-gray-500 select-all truncate" title={url}>URL: {url || '(not available)'} </div>
          </div>
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="aspect-video rounded-md bg-gray-100 overflow-hidden relative">
              {!imgUrl && <div className="absolute inset-0 grid place-content-center text-gray-500">Preview unavailable</div>}
              {!!imgUrl && (
                // Use <img> with cache-busting timestamp param
                <img src={imgUrl} alt="Browser preview" className="w-full h-full object-contain" onError={() => setError('Preview unavailable')} />
              )}
              {loading && <div className="absolute bottom-2 right-2 text-xs bg-white/80 rounded px-2 py-0.5">Refreshing...</div>}
              {error && <div className="absolute bottom-2 left-2 text-xs bg-rose-100 text-rose-700 rounded px-2 py-0.5">{error}</div>}
              <div className="absolute top-2 right-2">
                <button onClick={refresh} className="rounded bg-sky-600 px-2 py-1 text-white text-xs hover:bg-sky-700">Refresh</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function ScheduleBox({ disabled }) {
  const [ts, setTs] = useState('')
  const [scheduledAt, setScheduledAt] = useState(null)
  async function schedule() {
    if (!ts) return
    const epoch = Date.parse(ts) / 1000
    await apiFetch(`${API_BASE}/schedule`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ start_at: epoch }) })
    const res = await apiFetch(`${API_BASE}/schedule`)
    const data = await res.json()
    setScheduledAt(data.at)
  }
  async function cancel() {
    await apiFetch(`${API_BASE}/schedule/cancel`, { method: 'POST' })
    setScheduledAt(null)
  }
  useEffect(() => {
    let cancel = false
    async function load() {
      const res = await apiFetch(`${API_BASE}/schedule`)
      const data = await res.json()
      if (!cancel) setScheduledAt(data.at)
    }
    load()
    return () => { cancel = true }
  }, [])
  return (
    <div className="mt-4 rounded border p-3">
      <div className="text-sm font-medium">Schedule</div>
      <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-2 items-center">
        <input type="datetime-local" value={ts} onChange={e=>setTs(e.target.value)} className="rounded border px-2 py-1" />
        <button disabled={disabled || !ts} onClick={schedule} className="rounded bg-indigo-600 px-3 py-2 text-white text-sm hover:bg-indigo-700 disabled:opacity-50">Schedule Start</button>
        <button disabled={disabled || !scheduledAt} onClick={cancel} className="rounded bg-gray-600 px-3 py-2 text-white text-sm hover:bg-gray-700 disabled:opacity-50">Cancel</button>
      </div>
      {scheduledAt && <div className="mt-2 text-xs text-gray-600">Scheduled for: {new Date(scheduledAt*1000).toLocaleString()}</div>}
    </div>
  )
}

function Dashboard() {
  const [status, setStatus] = useState({ running: false, browser_open: false, has_driver: false, timer: { started: false, ended: false, elapsed_seconds: null } })
  const [busy, setBusy] = useState(false)

  async function fetchStatus() {
    try {
      const res = await apiFetch(`${API_BASE}/status`)
      const data = await res.json()
      setStatus(data)
    } catch (err) {
      console.error('status fetch failed', err)
    }
  }

  async function openBrowser() {
    setBusy(true)
    try {
      await apiFetch(`${API_BASE}/open-browser`, { method: 'POST' })
      await fetchStatus()
    } finally { setBusy(false) }
  }

  async function openLocalBrowser() {
    setBusy(true)
    try {
      const response = await apiFetch(`${API_BASE}/open-local-browser`, { method: 'POST' })
      const data = await response.json()
      if (data.ok) {
        alert(`Browser opened locally! Navigate to: ${data.url}`)
      } else {
        alert(`Failed to open browser: ${data.error}`)
      }
    } catch (err) {
      alert('Failed to open local browser. Make sure the server is running locally.')
    } finally { setBusy(false) }
  }

  async function startBot() {
    setBusy(true)
    try {
      await apiFetch(`${API_BASE}/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ open_browser: true }) })
      await fetchStatus()
    } finally { setBusy(false) }
  }

  async function stopBot() {
    setBusy(true)
    try {
      await apiFetch(`${API_BASE}/stop`, { method: 'POST' })
      await fetchStatus()
    } finally { setBusy(false) }
  }

  async function closeBrowser() {
    setBusy(true)
    try {
      await apiFetch(`${API_BASE}/close-browser`, { method: 'POST' })
      await fetchStatus()
    } finally { setBusy(false) }
  }

  useEffect(() => { fetchStatus() }, [])

  return (
    <section id="dashboard" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center justify-between">
        <h2 className="text-xl sm:text-2xl font-semibold">Dashboard</h2>
        <div className="flex items-center gap-2">
          <Badge color={status.running ? 'green' : 'gray'}>Running: {String(status.running)}</Badge>
          <Badge color={status.browser_open ? 'sky' : 'gray'}>Browser: {String(status.browser_open)}</Badge>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border bg-white p-4">
          <h3 className="font-medium">Browser Control</h3>
          <p className="text-sm text-gray-600">Choose browser mode for interaction.</p>
          
          <div className="mt-3 space-y-2">
            <div className="text-xs font-medium text-gray-700">Local Browser (Manual Login)</div>
            <button
              disabled={busy}
              onClick={openLocalBrowser}
              className="w-full inline-flex items-center justify-center rounded-md bg-green-600 px-3 py-2 text-white text-sm hover:bg-green-700 disabled:opacity-50"
            >🌐 Open TTD Site Locally</button>
            <div className="text-xs text-gray-500">Opens TTD website in your default browser for manual login</div>
          </div>

          <hr className="my-3" />

          <div className="space-y-2">
            <div className="text-xs font-medium text-gray-700">Remote Browser (Bot Control)</div>
            <button
              disabled={busy || status.browser_open}
              onClick={openBrowser}
              className="w-full inline-flex items-center justify-center rounded-md bg-sky-600 px-3 py-2 text-white text-sm hover:bg-sky-700 disabled:opacity-50"
            >🤖 Open Remote Browser</button>
            <button
              disabled={busy || !status.browser_open}
              onClick={closeBrowser}
              className="w-full inline-flex items-center justify-center rounded-md bg-gray-600 px-3 py-2 text-white text-sm hover:bg-gray-700 disabled:opacity-50"
            >Close Remote Browser</button>
            <div className="text-xs text-gray-500">Headless browser on server for automation</div>
          </div>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <h3 className="font-medium">Bot</h3>
          <p className="text-sm text-gray-600">Start/Stop automation.</p>
          <div className="mt-3 flex gap-2">
            <button disabled={busy || status.running} onClick={startBot} className="inline-flex items-center justify-center rounded-md bg-emerald-600 px-3 py-2 text-white text-sm hover:bg-emerald-700 disabled:opacity-50">Start</button>
            <button disabled={busy || !status.running} onClick={stopBot} className="inline-flex items-center justify-center rounded-md bg-rose-600 px-3 py-2 text-white text-sm hover:bg-rose-700 disabled:opacity-50">Stop</button>
          </div>
          <ScheduleBox disabled={busy} />
          <div className="mt-3 text-xs text-gray-500">Has driver: {String(status.has_driver)}</div>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <h3 className="font-medium">Timer</h3>
          <p className="text-sm text-gray-600">Measures fill duration.</p>
          <TimerBox started={status?.timer?.started} ended={status?.timer?.ended} elapsed={status?.timer?.elapsed_seconds} />
        </div>
        <div className="rounded-lg border bg-white p-4">
          <h3 className="font-medium">Config</h3>
          <p className="text-sm text-gray-600">Edit Srivari Group and Members.</p>
          <a href="#config" className="mt-3 inline-flex items-center justify-center rounded-md border px-3 py-2 text-sm hover:bg-gray-50">Open Config</a>
        </div>
      </div>
    </section>
  )
}

function MemberRow({ index, value, onChange, onRemove, disabledRemove, onMoveUp, onMoveDown, canMoveUp, canMoveDown }) {
  const bloodGroups = useMemo(() => (['O+','O-','A+','A-','B+','B-','AB+','AB-']), [])
  const genders = useMemo(() => (['Male','Female','Other']), [])
  const idTypes = useMemo(() => (['Aadhaar','PAN','Driving License','Voter ID','Passport']), [])

  function set(k, v) { onChange({ ...value, [k]: v }) }

  return (
    <div className="rounded border p-3 bg-white">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge color="amber">#{index + 1}</Badge>
          <span className="text-sm text-gray-600">Member</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onMoveUp} disabled={!canMoveUp} className="rounded border px-2 py-1 text-xs hover:bg-gray-50 disabled:opacity-50">↑</button>
          <button onClick={onMoveDown} disabled={!canMoveDown} className="rounded border px-2 py-1 text-xs hover:bg-gray-50 disabled:opacity-50">↓</button>
          <button onClick={onRemove} disabled={disabledRemove} className="rounded bg-rose-600 px-2 py-1 text-white text-xs hover:bg-rose-700 disabled:opacity-50">Remove</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Field label="Name*">
          <input value={value.name||''} onChange={e=>set('name', e.target.value)} className="w-full rounded border px-2 py-1" placeholder="Full name" />
        </Field>
        <Field label="DOB*" hint="YYYY-MM-DD">
          <input type="date" value={value.dob||''} onChange={e=>set('dob', e.target.value)} className="w-full rounded border px-2 py-1" />
        </Field>
        <Field label="Age*">
          <input inputMode="numeric" value={value.age||''} onChange={e=>set('age', e.target.value)} className="w-full rounded border px-2 py-1" placeholder="e.g., 30" />
        </Field>
        <Field label="Blood Group*">
          <select value={value.blood_group||''} onChange={e=>set('blood_group', e.target.value)} className="w-full rounded border px-2 py-1">
            <option value="">Select</option>
            {bloodGroups.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </Field>
        <Field label="Gender*">
          <select value={value.gender||'Male'} onChange={e=>set('gender', e.target.value)} className="w-full rounded border px-2 py-1">
            {genders.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </Field>
        <Field label="ID Type*">
          <select value={value.id_proof_type||'Aadhaar'} onChange={e=>set('id_proof_type', e.target.value)} className="w-full rounded border px-2 py-1">
            {idTypes.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </Field>
        <Field label="ID Number*">
          <input value={value.id_number||''} onChange={e=>set('id_number', e.target.value)} className="w-full rounded border px-2 py-1" placeholder="XXXX-XXXX-XXXX" />
        </Field>
        <Field label="Mobile*">
          <input inputMode="tel" value={value.mobile||''} onChange={e=>set('mobile', e.target.value)} className="w-full rounded border px-2 py-1" placeholder="10-digit number" />
        </Field>
        <Field label="Email*">
          <input type="email" value={value.email||''} onChange={e=>set('email', e.target.value)} className="w-full rounded border px-2 py-1" placeholder="name@email.com" />
        </Field>
        <Field label="State">
          <input value={value.state||''} onChange={e=>set('state', e.target.value)} className="w-full rounded border px-2 py-1" />
        </Field>
        <Field label="District">
          <input value={value.district||''} onChange={e=>set('district', e.target.value)} className="w-full rounded border px-2 py-1" />
        </Field>
        <Field label="City">
          <input value={value.city||''} onChange={e=>set('city', e.target.value)} className="w-full rounded border px-2 py-1" />
        </Field>
        <Field label="Street">
          <input value={value.street||''} onChange={e=>set('street', e.target.value)} className="w-full rounded border px-2 py-1" />
        </Field>
        <Field label="Door No">
          <input value={value.doorno||''} onChange={e=>set('doorno', e.target.value)} className="w-full rounded border px-2 py-1" />
        </Field>
        <Field label="Pincode">
          <input inputMode="numeric" value={value.pincode||''} onChange={e=>set('pincode', e.target.value)} className="w-full rounded border px-2 py-1" />
        </Field>
        <Field label="Nearest TTD Temple">
          <input value={value.nearest_ttd_temple||''} onChange={e=>set('nearest_ttd_temple', e.target.value)} className="w-full rounded border px-2 py-1" placeholder="Type temple name as on site" />
        </Field>
        <Field label="Photo*" hint="Current photo shown below. Use Browse to change.">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded bg-sky-600 px-2 py-1 text-white text-xs hover:bg-sky-700"
                onClick={() => {
                  const input = document.getElementById(`photo-input-${index}`)
                  if (input) input.click()
                }}
              >Browse</button>
              {value.photo && <span className="text-xs text-gray-600 truncate" title={value.photo}>{value.photo}</span>}
            </div>
            <input
              id={`photo-input-${index}`}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={async (e) => {
                const file = e.target.files?.[0]
                if (!file) return
                try {
                  const form = new FormData()
                  form.append('file', file)
                  const res = await apiFetch(`${API_BASE}/upload-photo`, { method: 'POST', body: form })
                  const data = await res.json()
                  if (data?.path) set('photo', data.path)
                } catch (err) {
                  console.error('upload failed', err)
                } finally {
                  e.target.value = '' // allow re-select same file
                }
              }}
            />
            {value.photo ? (
              <img
                src={(function(){
                  let p = (value.photo || '').trim()
                  if (!p) return ''
                  // Normalize backslashes to forward slashes
                  p = p.replace(/\\/g, '/')
                  // Absolute URL
                  if (/^https?:\/\//i.test(p)) return p
                  // Already includes server prefix
                  if (p.startsWith(`${API_BASE}/`) || p.startsWith('http://127.0.0.1:8000/') || p.startsWith('http://localhost:8000/')) return p
                  // Serve known relative paths via API server
                  if (p.startsWith('/uploads/') || p.startsWith('uploads/') || p.startsWith('/images/') || p.startsWith('images/')) {
                    const rel = p.startsWith('/') ? p : `/${p}`
                    return `${API_BASE}${rel}`
                  }
                  // Windows drive path or other local path cannot be previewed by browser directly
                  return ''
                })()}
                alt="Member photo"
                title={value.photo || ''}
                className="h-24 w-24 object-cover rounded border"
                onError={(e)=>{ e.currentTarget.src=''; }}
              />
            ) : (
              <div className="h-24 w-24 grid place-content-center text-xs text-gray-500 border rounded">No photo</div>
            )}
          </div>
        </Field>
      </div>
    </div>
  )
}

function ConfigEditor() {
  const [webhookUrl, setWebhookUrl] = useState('')
  const [general, setGeneral] = useState({ group_size: '', download_dir: '', auto_select_date: true, auto_download_ticket: true, respect_existing: true, aadhaar_autofill_wait_seconds: 6 })
  const [members, setMembers] = useState([])
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => { reload() }, [])

  async function reload() {
    setLoading(true)
    try {
      const res = await apiFetch(`${API_BASE}/config`)
      const data = await res.json()
      setGeneral({
        group_size: data?.general?.group_size ?? '',
        download_dir: data?.general?.download_dir ?? '',
        auto_select_date: !!data?.general?.auto_select_date,
        auto_download_ticket: !!data?.general?.auto_download_ticket,
        respect_existing: data?.general?.respect_existing ?? true,
        aadhaar_autofill_wait_seconds: data?.general?.aadhaar_autofill_wait_seconds ?? 6,
      })
      setWebhookUrl(data?.general?.webhook_url || '')
      const arr = Array.isArray(data?.members) ? data.members : []
      setMembers(arr.slice(0, 10))
    } catch (e) {
      console.error('config fetch failed', e)
    } finally {
      setLoading(false)
    }
  }

  function setMember(idx, next) {
    setMembers(prev => prev.map((m, i) => i === idx ? next : m))
  }
  function addMember() {
    setMembers(prev => prev.length >= 10 ? prev : [...prev, { gender: 'Male', id_proof_type: 'Aadhaar' }])
  }
  function removeMember(idx) {
    setMembers(prev => prev.filter((_, i) => i !== idx))
  }

  async function saveConfig() {
    setSaving(true)
    try {
      const payload = {
        general: {
          group_size: general.group_size ? Number(general.group_size) : undefined,
          download_dir: general.download_dir || undefined,
          auto_select_date: !!general.auto_select_date,
          auto_download_ticket: !!general.auto_download_ticket,
          respect_existing: !!general.respect_existing,
          aadhaar_autofill_wait_seconds: Number(general.aadhaar_autofill_wait_seconds || 6),
          webhook_url: webhookUrl || undefined,
        },
        members: members,
      }
      // Client-side DOB validation and age auto-calc
      try {
        const min = new Date(1965, 8, 1) // 01/09/1965 (month is 0-based)
        const max = new Date(2007, 8, 1) // 01/09/2007
        const invalid = []
        const fixedMembers = members.map((m, i) => {
          const next = { ...m }
          if (next.dob) {
            // dob is yyyy-mm-dd from input type=date
            const [Y, M, D] = String(next.dob).split('-').map(Number)
            if (Y && M && D) {
              const d = new Date(Y, (M - 1), D)
              if (isNaN(d.getTime()) || d < min || d > max) invalid.push(i)
              // auto-calc age if missing
              if (!next.age) {
                const today = new Date()
                let age = today.getFullYear() - Y
                const beforeBirthday = (today.getMonth() + 1 < M) || ((today.getMonth() + 1 === M) && today.getDate() < D)
                if (beforeBirthday) age -= 1
                next.age = String(age)
              }
            }
          }
          return next
        })
        if (invalid.length) {
          alert(`Invalid DOB for member(s): ${invalid.map(i=>i+1).join(', ')}. Allowed range: 01/09/1965 to 01/09/2007.`)
          return
        }
        payload.members = fixedMembers
      } catch (e) {
        console.warn('DOB validation skipped due to error', e)
      }
      await apiFetch(`${API_BASE}/config`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    } catch (e) {
      console.error('config save failed', e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section id="config" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center justify-between">
        <h2 className="text-xl sm:text-2xl font-semibold">Configuration</h2>
        <div className="flex gap-2">
          <button onClick={reload} disabled={loading} className="inline-flex items-center justify-center rounded-md border px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50">Reload</button>
          <button disabled={saving} onClick={saveConfig} className="inline-flex items-center justify-center rounded-md bg-sky-600 px-3 py-2 text-white text-sm hover:bg-sky-700 disabled:opacity-50">Save</button>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4">
        <div className="rounded-lg border bg-white p-4">
          <h3 className="font-medium">Srivari Seva Group Settings</h3>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Field label="Webhook URL" hint="Optional: receives JSON notifications for events like start/stop.">
              <input value={webhookUrl} onChange={e=>setWebhookUrl(e.target.value)} className="w-full rounded border px-2 py-1" placeholder="https://example.com/webhook" />
            </Field>
            <Field label="Group Size*">
              <input value={general.group_size} onChange={e=>setGeneral(g=>({...g, group_size: e.target.value}))} className="w-full rounded border px-2 py-1" placeholder="e.g., 5" />
            </Field>
            <Field label="Download Folder">
              <input value={general.download_dir} onChange={e=>setGeneral(g=>({...g, download_dir: e.target.value}))} className="w-full rounded border px-2 py-1" placeholder="C:\\path\\to\\downloads" />
            </Field>
            <Field label="Auto select date">
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={general.auto_select_date} onChange={e=>setGeneral(g=>({...g, auto_select_date: e.target.checked}))} />
                <span className="text-sm text-gray-700">Enable</span>
              </div>
            </Field>
            <Field label="Auto download ticket">
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={general.auto_download_ticket} onChange={e=>setGeneral(g=>({...g, auto_download_ticket: e.target.checked}))} />
                <span className="text-sm text-gray-700">Enable</span>
              </div>
            </Field>
            <Field label="Respect existing data">
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={general.respect_existing} onChange={e=>setGeneral(g=>({...g, respect_existing: e.target.checked}))} />
                <span className="text-sm text-gray-700">Do not overwrite fields prefilled by the website</span>
              </div>
            </Field>
            <Field label="Autofill wait (seconds)">
              <input inputMode="numeric" value={general.aadhaar_autofill_wait_seconds} onChange={e=>setGeneral(g=>({...g, aadhaar_autofill_wait_seconds: Number(e.target.value||6)}))} className="w-full rounded border px-2 py-1" />
            </Field>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Members (up to 10)</h3>
            <div className="flex items-center gap-2">
              <input id="import-csv-input" type="file" accept=".csv" style={{display:'none'}} onChange={async (e)=>{
                const file = e.target.files?.[0]; if (!file) return
                try {
                  const form = new FormData(); form.append('file', file)
                  const res = await apiFetch(`${API_BASE}/import-csv`, { method: 'POST', body: form })
                  const data = await res.json()
                  if (Array.isArray(data?.members)) {
                    setMembers(prev => [...prev, ...data.members].slice(0, 10))
                  }
                } catch(err) { console.error('import failed', err) }
                finally { e.target.value = '' }
              }} />
              <button onClick={()=>document.getElementById('import-csv-input')?.click()} className="inline-flex items-center justify-center rounded-md border px-2 py-1 text-sm hover:bg-gray-50">Import CSV</button>
              <a href={`${API_BASE}/export/csv`} className="inline-flex items-center justify-center rounded-md border px-2 py-1 text-sm hover:bg-gray-50">Export CSV</a>
              <a href={`${API_BASE}/export/json`} className="inline-flex items-center justify-center rounded-md border px-2 py-1 text-sm hover:bg-gray-50">Export JSON</a>
              <button onClick={addMember} disabled={members.length >= 10} className="inline-flex items-center justify-center rounded-md border px-2 py-1 text-sm hover:bg-gray-50 disabled:opacity-50">Add Member</button>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3">
            {members.length === 0 && <div className="text-sm text-gray-500">No members yet. Click "Add Member" to start.</div>}
            {members.map((m, idx) => (
              <MemberRow
                key={idx}
                index={idx}
                value={m}
                onChange={next => setMember(idx, next)}
                onRemove={() => removeMember(idx)}
                onMoveUp={() => setMembers(prev => { if (idx===0) return prev; const copy=[...prev]; const [it]=copy.splice(idx,1); copy.splice(idx-1,0,it); return copy })}
                onMoveDown={() => setMembers(prev => { if (idx>=prev.length-1) return prev; const copy=[...prev]; const [it]=copy.splice(idx,1); copy.splice(idx+1,0,it); return copy })}
                canMoveUp={idx > 0}
                canMoveDown={idx < members.length - 1}
                disabledRemove={members.length === 0}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function Logs() {
  const [items, setItems] = useState([])
  const latestRef = useRef(0)

  useEffect(() => {
    let cancelled = false
    async function tick() {
      try {
        const res = await apiFetch(`${API_BASE}/logs?since=${latestRef.current}`)
        const data = await res.json()
        if (!cancelled) {
          if (Array.isArray(data.items) && data.items.length) {
            latestRef.current = data.latest || latestRef.current
            setItems(prev => [...prev, ...data.items].slice(-1000))
          }
        }
      } catch (err) {
        console.error('logs fetch failed', err)
      }
      if (!cancelled) setTimeout(tick, 1000)
    }
    tick()
    return () => { cancelled = true }
  }, [])

  return (
    <section id="logs" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-12">
      <h2 className="text-xl sm:text-2xl font-semibold">Activity Logs</h2>
      <div className="mt-4 rounded-lg border bg-white p-4">
        <div className="h-64 overflow-auto text-sm text-gray-700 space-y-1">
          {items.length === 0 && <div className="text-gray-400">(Logs will appear here)</div>}
          {items.map(it => (
            <div key={it.seq}>[{it.ts}] {it.msg}</div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Login({ onLoggedIn }) {
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function doLogin() {
    setBusy(true); setError('')
    try {
      const res = await apiFetch(`${API_BASE}/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) })
      if (!res.ok) throw new Error('Invalid credentials')
      onLoggedIn()
    } catch (e) {
      setError('Login failed', e)
    } finally { setBusy(false) }
  }
  return (
    <div className="mx-auto max-w-sm py-24">
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Login</h2>
        <div className="mt-3">
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Admin password" className="w-full rounded border px-3 py-2" />
        </div>
        {error && <div className="mt-2 text-sm text-rose-600">{error}</div>}
        <button disabled={busy} onClick={doLogin} className="mt-4 w-full rounded bg-sky-600 px-3 py-2 text-white text-sm hover:bg-sky-700 disabled:opacity-50">Sign in</button>
      </div>
    </div>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)
  
  // Auto-login if auth is disabled
  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await apiFetch(`${API_BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: 'test' })
        })
        const data = await res.json()
        if (data.ok && data.note === 'auth disabled') {
          setAuthed(true)
        }
      } catch (e) {
        console.log('Auth check failed, showing login form', e)
      } finally {
        setAuthChecked(true)
      }
    }
    checkAuth()
  }, [])
  
  async function logout() { await apiFetch(`${API_BASE}/logout`, { method: 'POST' }); setAuthed(false) }
  
  if (!authChecked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full mx-auto"></div>
          <div className="mt-2 text-gray-600">Loading TTD Bot...</div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {authed ? (
        <>
          <Navbar onLogout={logout} />
          <Hero />
          <Dashboard />
          <ConfigEditor />
          <Logs />
        </>
      ) : (
        <Login onLoggedIn={()=>setAuthed(true)} />
      )}
    </div>
  )
}
