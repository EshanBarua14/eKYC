/**
 * PEP List Management - BFIU s4.2
 */
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'react-hot-toast'
import { API, getToken } from '../../config'
import { Shield, Plus, Search, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'

const apiFetch = (path, opts={}) => {
  const tok = getToken() || localStorage.getItem('ekyc_admin_token') || ''
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type':'application/json', Authorization:`Bearer ${tok}`, ...(opts.headers||{}) }
  }).then(r => r.json())
}

export default function PEPManagementPage() {
  const [entries, setEntries] = useState([])
  const [total,   setTotal]   = useState(0)
  const [loading, setLoading] = useState(true)
  const [search,  setSearch]  = useState('')
  const [page,    setPage]    = useState(1)
  const pageSize = 50
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({
    full_name_en:'', full_name_bn:'', category:'PEP',
    position:'', ministry_or_org:'', nationality:'BD',
    risk_level:'HIGH', notes:''
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const offset = (page - 1) * pageSize
      const params = new URLSearchParams({ limit: pageSize, offset })
      if (search) params.set('search', search)
      const d = await apiFetch(`/api/v1/pep/entries?${params}`)
      if (Array.isArray(d)) { setEntries(d); setTotal(d.length) }
      else { setEntries(d.entries || []); setTotal(d.total || 0) }
    } catch(e) { console.error(e); setEntries([]) }
    finally { setLoading(false) }
  }, [page, search])

  useEffect(() => { load() }, [load])

  const addEntry = async () => {
    try {
      await apiFetch('/api/v1/pep/entries', { method:'POST', body: JSON.stringify(form) })
      toast.success('PEP entry added (BFIU s4.2)')
      setShowAdd(false)
      setForm({ full_name_en:'', full_name_bn:'', category:'PEP', position:'', ministry_or_org:'', nationality:'BD', risk_level:'HIGH', notes:'' })
      load()
    } catch(e) { toast.error('Failed to add PEP entry') }
  }

  const deactivate = async (id) => {
    try {
      await apiFetch(`/api/v1/pep/entries/${id}/deactivate`, { method:'PATCH' })
      toast.success('Entry deactivated')
      load()
    } catch { toast.error('Failed to deactivate') }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div style={{padding:'24px', fontFamily:'sans-serif'}}>
      {/* Header */}
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'16px'}}>
        <div>
          <h2 style={{margin:0, fontSize:'22px', fontWeight:700}}>PEP List Management</h2>
          <p style={{margin:'4px 0 0', color:'#666', fontSize:'13px'}}>
            Politically Exposed Persons · BFIU s4.2 · {total.toLocaleString()} total entries
          </p>
        </div>
        <button onClick={() => setShowAdd(true)}
          style={{background:'#4f46e5', color:'#fff', border:'none', borderRadius:'8px',
                  padding:'8px 16px', cursor:'pointer', display:'flex', alignItems:'center', gap:'6px'}}>
          <Plus size={16}/> Add PEP Entry
        </button>
      </div>

      {/* BFIU notice */}
      <div style={{background:'#fefce8', border:'1px solid #fde047', borderRadius:'8px',
                   padding:'10px 14px', marginBottom:'16px', fontSize:'13px', color:'#854d0e'}}>
        BFIU s4.2: PEP/IP customers require EDD. Any match triggers Enhanced Due Diligence automatically.
      </div>

      {/* Search + Refresh */}
      <div style={{display:'flex', gap:'8px', marginBottom:'16px'}}>
        <div style={{position:'relative', flex:1}}>
          <Search size={14} style={{position:'absolute', left:'10px', top:'50%', transform:'translateY(-50%)', color:'#999'}}/>
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}
            placeholder='Search by name, category, position...'
            style={{width:'100%', padding:'8px 8px 8px 32px', border:'1px solid #e5e7eb',
                    borderRadius:'8px', fontSize:'13px', boxSizing:'border-box'}}/>
        </div>
        <button onClick={load}
          style={{background:'#f3f4f6', border:'1px solid #e5e7eb', borderRadius:'8px',
                  padding:'8px 14px', cursor:'pointer', display:'flex', alignItems:'center', gap:'6px', fontSize:'13px'}}>
          <RefreshCw size={14}/> Refresh
        </button>
        <span style={{padding:'8px 12px', background:'#f3f4f6', borderRadius:'8px',
                      fontSize:'13px', color:'#666', border:'1px solid #e5e7eb'}}>
          {loading ? 'Loading...' : `${entries.length} results`}
        </span>
      </div>

      {/* Table */}
      <div style={{border:'1px solid #e5e7eb', borderRadius:'10px', overflow:'hidden'}}>
        <table style={{width:'100%', borderCollapse:'collapse', fontSize:'13px'}}>
          <thead>
            <tr style={{background:'#f9fafb', borderBottom:'1px solid #e5e7eb'}}>
              {['Name','Bangla Name','Category','Position / Org','Country','Risk','Source','Status','Action'].map(h => (
                <th key={h} style={{padding:'10px 12px', textAlign:'left', fontWeight:600, color:'#374151', whiteSpace:'nowrap'}}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} style={{padding:'40px', textAlign:'center', color:'#999'}}>Loading...</td></tr>
            ) : entries.length === 0 ? (
              <tr><td colSpan={9} style={{padding:'40px', textAlign:'center', color:'#999'}}>No PEP entries found</td></tr>
            ) : entries.map((e, i) => (
              <tr key={e.id} style={{borderBottom:'1px solid #f3f4f6', background: i%2===0 ? '#fff' : '#fafafa'}}>
                <td style={{padding:'8px 12px', fontWeight:500}}>{e.full_name_en}</td>
                <td style={{padding:'8px 12px', color:'#666'}}>{e.full_name_bn || '-'}</td>
                <td style={{padding:'8px 12px'}}>
                  <span style={{background: e.category==='PEP' ? '#dbeafe' : '#dcfce7',
                                color: e.category==='PEP' ? '#1d4ed8' : '#166534',
                                padding:'2px 8px', borderRadius:'4px', fontSize:'11px', fontWeight:600}}>
                    {e.category}
                  </span>
                </td>
                <td style={{padding:'8px 12px', color:'#555', maxWidth:'200px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                  {[e.position, e.ministry_or_org].filter(Boolean).join(' · ') || '-'}
                </td>
                <td style={{padding:'8px 12px'}}>{e.country || 'BD'}</td>
                <td style={{padding:'8px 12px'}}>
                  <span style={{background: e.risk_level==='HIGH' ? '#fee2e2' : '#fef9c3',
                                color: e.risk_level==='HIGH' ? '#991b1b' : '#854d0e',
                                padding:'2px 8px', borderRadius:'4px', fontSize:'11px', fontWeight:600}}>
                    {e.risk_level}
                  </span>
                </td>
                <td style={{padding:'8px 12px', fontSize:'11px', color:'#888'}}>{e.source || 'MANUAL'}</td>
                <td style={{padding:'8px 12px'}}>
                  <span style={{background: e.status==='ACTIVE' ? '#dcfce7' : '#f3f4f6',
                                color: e.status==='ACTIVE' ? '#166534' : '#6b7280',
                                padding:'2px 8px', borderRadius:'4px', fontSize:'11px', fontWeight:600}}>
                    {e.status}
                  </span>
                </td>
                <td style={{padding:'8px 12px'}}>
                  {e.status === 'ACTIVE' && (
                    <button onClick={() => deactivate(e.id)}
                      style={{background:'#fee2e2', color:'#991b1b', border:'none', borderRadius:'4px',
                              padding:'3px 8px', cursor:'pointer', fontSize:'11px'}}>
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center',
                     marginTop:'12px', fontSize:'13px', color:'#666'}}>
          <span>Page {page} of {totalPages} · {total.toLocaleString()} total entries</span>
          <div style={{display:'flex', gap:'6px'}}>
            <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1}
              style={{padding:'6px 10px', border:'1px solid #e5e7eb', borderRadius:'6px',
                      cursor: page===1 ? 'not-allowed' : 'pointer', background:'#fff',
                      display:'flex', alignItems:'center', opacity: page===1 ? 0.5 : 1}}>
              <ChevronLeft size={14}/>
            </button>
              {(() => {
                const sp = Math.max(1, Math.min(page-2, totalPages-4))
                const btns = []
                for (let pi = sp; pi <= Math.min(sp+4, totalPages); pi++) {
                  btns.push(<button key={"p"+pi} onClick={() => setPage(pi)}
                    style={{padding:"6px 12px", border:"1px solid #e5e7eb", borderRadius:"6px", cursor:"pointer",
                            background: pi===page?"#4f46e5":"#fff", color: pi===page?"#fff":"#374151",
                            fontWeight: pi===page?600:400, minWidth:"36px"}}>
                    {pi}
                  </button>)
                }
                return btns
              })()}
            <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page===totalPages}
              style={{padding:'6px 10px', border:'1px solid #e5e7eb', borderRadius:'6px',
                      cursor: page===totalPages ? 'not-allowed' : 'pointer', background:'#fff',
                      display:'flex', alignItems:'center', opacity: page===totalPages ? 0.5 : 1}}>
              <ChevronRight size={14}/>
            </button>
          </div>
        </div>
      )}

      {/* Add PEP Modal */}
      {showAdd && (
        <div style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.5)',
                     display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000}}>
          <div style={{background:'#fff', borderRadius:'12px', padding:'24px', width:'480px', maxHeight:'80vh', overflowY:'auto'}}>
            <div style={{display:'flex', justifyContent:'space-between', marginBottom:'16px'}}>
              <h3 style={{margin:0}}>Add PEP Entry</h3>
              <button onClick={() => setShowAdd(false)} style={{background:'none', border:'none', cursor:'pointer', fontSize:'18px'}}>x</button>
            </div>
            {[
              ['full_name_en','Full Name (English)*','text'],
              ['full_name_bn','Full Name (Bangla)','text'],
              ['position','Position','text'],
              ['ministry_or_org','Ministry / Organization','text'],
              ['notes','Notes','text'],
            ].map(([key, label]) => (
              <div key={key} style={{marginBottom:'12px'}}>
                <label style={{display:'block', fontSize:'12px', color:'#666', marginBottom:'4px'}}>{label}</label>
                <input value={form[key]||''} onChange={e => setForm(f => ({...f, [key]: e.target.value}))}
                  style={{width:'100%', padding:'8px', border:'1px solid #e5e7eb', borderRadius:'6px',
                          fontSize:'13px', boxSizing:'border-box'}}/>
              </div>
            ))}
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'16px'}}>
              <div>
                <label style={{display:'block', fontSize:'12px', color:'#666', marginBottom:'4px'}}>Category</label>
                <select value={form.category} onChange={e => setForm(f => ({...f, category: e.target.value}))}
                  style={{width:'100%', padding:'8px', border:'1px solid #e5e7eb', borderRadius:'6px', fontSize:'13px'}}>
                  {['PEP','IP','PEP_FAMILY','PEP_ASSOCIATE'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label style={{display:'block', fontSize:'12px', color:'#666', marginBottom:'4px'}}>Risk Level</label>
                <select value={form.risk_level} onChange={e => setForm(f => ({...f, risk_level: e.target.value}))}
                  style={{width:'100%', padding:'8px', border:'1px solid #e5e7eb', borderRadius:'6px', fontSize:'13px'}}>
                  {['HIGH','MEDIUM','LOW'].map(r => <option key={r}>{r}</option>)}
                </select>
              </div>
            </div>
            <div style={{display:'flex', gap:'8px', justifyContent:'flex-end'}}>
              <button onClick={() => setShowAdd(false)}
                style={{padding:'8px 16px', border:'1px solid #e5e7eb', borderRadius:'6px',
                        cursor:'pointer', background:'#f9fafb', fontSize:'13px'}}>
                Cancel
              </button>
              <button onClick={addEntry}
                style={{padding:'8px 16px', background:'#4f46e5', color:'#fff', border:'none',
                        borderRadius:'6px', cursor:'pointer', fontSize:'13px', fontWeight:600}}>
                Add Entry
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
