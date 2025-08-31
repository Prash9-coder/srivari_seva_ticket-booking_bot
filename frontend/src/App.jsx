import './App.css'
import { useEffect, useRef, useState, useMemo } from 'react'

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

function Navbar() {
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
      const u = `http://127.0.0.1:8000/screenshot?t=${Date.now()}`
      // Optimistically set image URL (browser will request it directly)
      setImgUrl(u)
      const res2 = await fetch('http://127.0.0.1:8000/current-url')
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
              TTD Virtual Seva Booking Assistant
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

function Dashboard() {
  const [status, setStatus] = useState({ running: false, browser_open: false, has_driver: false })
  const [busy, setBusy] = useState(false)

  async function fetchStatus() {
    try {
      const res = await fetch('http://127.0.0.1:8000/status')
      const data = await res.json()
      setStatus(data)
    } catch (err) {
      console.error('status fetch failed', err)
    }
  }

  async function openBrowser() {
    setBusy(true)
    try {
      await fetch('http://127.0.0.1:8000/open-browser', { method: 'POST' })
      await fetchStatus()
    } finally { setBusy(false) }
  }

  async function startBot() {
    setBusy(true)
    try {
      await fetch('http://127.0.0.1:8000/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ open_browser: true }) })
      await fetchStatus()
    } finally { setBusy(false) }
  }

  async function stopBot() {
    setBusy(true)
    try {
      await fetch('http://127.0.0.1:8000/stop', { method: 'POST' })
      await fetchStatus()
    } finally { setBusy(false) }
  }

  async function closeBrowser() {
    setBusy(true)
    try {
      await fetch('http://127.0.0.1:8000/close-browser', { method: 'POST' })
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
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border bg-white p-4">
          <h3 className="font-medium">Browser</h3>
          <p className="text-sm text-gray-600">Open Chrome and navigate.</p>
          <button
            disabled={busy || status.browser_open}
            onClick={openBrowser}
            className="mt-3 inline-flex items-center justify-center rounded-md bg-sky-600 px-3 py-2 text-white text-sm hover:bg-sky-700 disabled:opacity-50"
          >Open Browser</button>
          <button
            disabled={busy || !status.browser_open}
            onClick={closeBrowser}
            className="mt-2 inline-flex items-center justify-center rounded-md bg-gray-600 px-3 py-2 text-white text-sm hover:bg-gray-700 disabled:opacity-50"
          >Close Browser</button>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <h3 className="font-medium">Bot</h3>
          <p className="text-sm text-gray-600">Start/Stop automation.</p>
          <div className="mt-3 flex gap-2">
            <button disabled={busy || status.running} onClick={startBot} className="inline-flex items-center justify-center rounded-md bg-emerald-600 px-3 py-2 text-white text-sm hover:bg-emerald-700 disabled:opacity-50">Start</button>
            <button disabled={busy || !status.running} onClick={stopBot} className="inline-flex items-center justify-center rounded-md bg-rose-600 px-3 py-2 text-white text-sm hover:bg-rose-700 disabled:opacity-50">Stop</button>
          </div>
          <div className="mt-3 text-xs text-gray-500">Has driver: {String(status.has_driver)}</div>
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

function MemberRow({ index, value, onChange, onRemove, disabledRemove }) {
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
        <button onClick={onRemove} disabled={disabledRemove} className="rounded bg-rose-600 px-2 py-1 text-white text-xs hover:bg-rose-700 disabled:opacity-50">Remove</button>
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
                  const res = await fetch('http://127.0.0.1:8000/upload-photo', { method: 'POST', body: form })
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
                  if (p.startsWith('http://127.0.0.1:8000/') || p.startsWith('http://localhost:8000/')) return p
                  // Serve known relative paths via API server
                  if (p.startsWith('/uploads/') || p.startsWith('uploads/') || p.startsWith('/images/') || p.startsWith('images/')) {
                    const rel = p.startsWith('/') ? p : `/${p}`
                    return `http://127.0.0.1:8000${rel}`
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
  const [general, setGeneral] = useState({ group_size: '', download_dir: '', auto_select_date: true, auto_download_ticket: true })
  const [members, setMembers] = useState([])
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => { reload() }, [])

  async function reload() {
    setLoading(true)
    try {
      const res = await fetch('http://127.0.0.1:8000/config')
      const data = await res.json()
      setGeneral({
        group_size: data?.general?.group_size ?? '',
        download_dir: data?.general?.download_dir ?? '',
        auto_select_date: !!data?.general?.auto_select_date,
        auto_download_ticket: !!data?.general?.auto_download_ticket,
      })
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
        },
        members: members,
      }
      await fetch('http://127.0.0.1:8000/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
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
          </div>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Members (up to 10)</h3>
            <button onClick={addMember} disabled={members.length >= 10} className="inline-flex items-center justify-center rounded-md border px-2 py-1 text-sm hover:bg-gray-50 disabled:opacity-50">Add Member</button>
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
        const res = await fetch(`http://127.0.0.1:8000/logs?since=${latestRef.current}`)
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

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <Hero />
      <Dashboard />
      <ConfigEditor />
      <Logs />
    </div>
  )
}
