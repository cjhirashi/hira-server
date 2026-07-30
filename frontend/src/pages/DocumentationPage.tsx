import { useEffect, useRef, useState } from 'react'
import ReactMarkdown, { Components } from 'react-markdown'
import { api } from '../services/api'
import { useAuthStore } from '../store/authStore'

// ── Types ─────────────────────────────────────────────────────────────────────

interface DocSummary {
  id: number
  title: string
  type: 'auto_script' | 'auto_inventory' | 'manual'
  source_type: string | null
  source_id: number | null
  generated_at: string
  updated_at: string
}
interface DocFull extends DocSummary { content_markdown: string }
interface Script { id: number; name: string }
interface RAGResult { chunk_id: number; document_id: number; document_title: string; content: string; score: number }

// ── Mermaid renderer ──────────────────────────────────────────────────────────

function MermaidBlock({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [svg, setSvg] = useState<string>('')

  useEffect(() => {
    let cancelled = false
    const id = `mermaid-${Math.random().toString(36).slice(2)}`
    import('mermaid').then(({ default: mermaid }) => {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark'
      mermaid.initialize({ theme: dark ? 'dark' : 'default', startOnLoad: false })
      mermaid.render(id, chart).then(({ svg: rendered }) => {
        if (!cancelled) setSvg(rendered)
      }).catch(() => {
        if (!cancelled) setSvg(`<pre style="color:var(--hira-alarm-critical)">${chart}</pre>`)
      })
    })
    return () => { cancelled = true }
  }, [chart])

  if (!svg) return <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>Renderizando diagrama…</div>
  return <div ref={ref} dangerouslySetInnerHTML={{ __html: svg }} style={{ overflow: 'auto', maxWidth: '100%' }} />
}

// ── Markdown con Mermaid ──────────────────────────────────────────────────────

const docComponents: Components = {
  code({ className, children }) {
    const lang = className?.replace('language-', '') ?? ''
    const text = String(children ?? '').trim()
    if (lang === 'mermaid') return <MermaidBlock chart={text} />
    return (
      <code
        style={{
          background: 'var(--bg-hover)',
          borderRadius: 'var(--radius-sm)',
          padding: lang ? '12px 16px' : '1px 5px',
          display: lang ? 'block' : 'inline',
          fontSize: 'var(--text-sm)',
          overflowX: 'auto',
          whiteSpace: 'pre',
        }}
      >
        {children}
      </code>
    )
  },
  h1: ({ children }) => <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--text-primary)', marginTop: 20, marginBottom: 6, borderBottom: '1px solid var(--border-subtle)', paddingBottom: 4 }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--accent)', marginTop: 14, marginBottom: 4 }}>{children}</h3>,
  h4: ({ children }) => <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginTop: 10, marginBottom: 4 }}>{children}</h4>,
  p: ({ children }) => <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.7, margin: '6px 0' }}>{children}</p>,
  table: ({ children }) => (
    <div style={{ overflowX: 'auto', marginBottom: 12 }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 'var(--text-sm)' }}>{children}</table>
    </div>
  ),
  th: ({ children }) => <th style={{ textAlign: 'left', padding: '6px 10px', borderBottom: '2px solid var(--border-default)', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase' }}>{children}</th>,
  td: ({ children }) => <td style={{ padding: '5px 10px', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}>{children}</td>,
}

function DocViewer({ content }: { content: string }) {
  return (
    <ReactMarkdown components={docComponents}>
      {content}
    </ReactMarkdown>
  )
}

// ── Type icons ────────────────────────────────────────────────────────────────
function TypeIcon({ type }: { type: string }) {
  if (type === 'auto_script') return <span title="Script auto-generado">📝</span>
  if (type === 'auto_inventory') return <span title="Inventario auto-generado">📋</span>
  return <span title="Manual">📄</span>
}

// ── Modal: crear/editar doc manual ───────────────────────────────────────────

function DocModal({ doc, onSave, onClose }: {
  doc: DocFull | null
  onSave: (title: string, content: string) => Promise<void>
  onClose: () => void
}) {
  const [title, setTitle] = useState(doc?.title ?? '')
  const [content, setContent] = useState(doc?.content_markdown ?? '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    if (!title.trim()) return
    setSaving(true)
    try { await onSave(title, content) } finally { setSaving(false) }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)', padding: 24, width: 640, maxHeight: '80vh', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--text-primary)' }}>{doc ? 'Editar documento' : 'Nuevo documento'}</div>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Título del documento"
          style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
        />
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="Contenido en Markdown…"
          rows={14}
          style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ ...btnBase, background: 'var(--bg-hover)', color: 'var(--text-primary)', border: '1px solid var(--border-default)' }}>Cancelar</button>
          <button onClick={save} disabled={saving || !title.trim()} style={{ ...btnBase, background: 'var(--accent)', color: '#fff' }}>
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── RAG Search Panel ─────────────────────────────────────────────────────────

function RAGSearchPanel() {
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<RAGResult[] | null>(null)

  const doSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const r = await api.post<RAGResult[]>('/rag/search', { query: query.trim(), top_k: 5 })
      setResults(r.data)
    } catch {
      setResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') doSearch()
  }

  return (
    <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 16, marginTop: 16 }}>
      <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
        Buscar en documentación
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Buscar en documentación…"
          style={{ ...inputStyle, flex: 1 }}
        />
        <button
          onClick={doSearch}
          disabled={searching || !query.trim()}
          style={{ ...btnBase, background: 'var(--accent)', color: '#fff' }}
        >
          {searching ? '…' : 'Buscar'}
        </button>
      </div>

      {results !== null && (
        <div>
          {results.length === 0 ? (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Sin resultados para esta búsqueda.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {results.map(r => (
                <div key={r.chunk_id} style={{ background: 'var(--bg-hover)', borderRadius: 'var(--radius-md)', padding: '10px 14px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)' }}>{r.document_title}</span>
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 8, background: 'var(--accent-subtle)', color: 'var(--accent)', fontWeight: 600 }}>
                      {(r.score * 100).toFixed(0)}% relevante
                    </span>
                  </div>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {r.content.slice(0, 400)}{r.content.length > 400 ? '…' : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DocumentationPage({ readonly = false }: { readonly?: boolean }) {
  const { isAdmin } = useAuthStore()
  const adminUser = isAdmin()
  const canEdit = adminUser && !readonly

  const [docs, setDocs] = useState<DocSummary[]>([])
  const [selected, setSelected] = useState<DocFull | null>(null)
  const [selectedChunkCount, setSelectedChunkCount] = useState<number | null>(null)
  const [modal, setModal] = useState<'create' | 'edit' | null>(null)
  const [toast, setToast] = useState<string>('')
  const [generating, setGenerating] = useState<string>('')
  const [indexing, setIndexing] = useState(false)
  const [indexingDoc, setIndexingDoc] = useState(false)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3500)
  }

  const loadDocs = async () => {
    const r = await api.get<DocSummary[]>('/docs')
    setDocs(r.data)
  }

  const loadDoc = async (id: number) => {
    const r = await api.get<DocFull>(`/docs/${id}`)
    setSelected(r.data)
    setSelectedChunkCount(null)
    // Cargar chunk count para badge
    try {
      const cr = await api.get<{ id: number }[]>(`/docs/${id}/chunks`)
      setSelectedChunkCount(cr.data.length)
    } catch {
      setSelectedChunkCount(0)
    }
  }

  useEffect(() => { loadDocs() }, [])

  // ── generate inventory
  const genInventory = async () => {
    setGenerating('Generando inventario…')
    try {
      const r = await api.post<DocFull>('/docs/generate/inventory')
      await loadDocs()
      setSelected(r.data)
      showToast('Inventario generado')
    } catch { showToast('Error generando inventario') }
    finally { setGenerating('') }
  }

  // ── generate all scripts
  const genAllScripts = async () => {
    try {
      const [logicRes, testRes] = await Promise.all([
        api.get<Script[]>('/logic'),
        api.get<Script[]>('/tests/scripts'),
      ])
      const logics = logicRes.data
      const tests = testRes.data
      const total = logics.length + tests.length
      let done = 0
      for (const s of logics) {
        setGenerating(`Generando ${++done}/${total}: ${s.name}`)
        await api.post(`/docs/generate/script/${s.id}?source_type=script_logic`).catch(() => {})
      }
      for (const s of tests) {
        setGenerating(`Generando ${++done}/${total}: ${s.name}`)
        await api.post(`/docs/generate/script/${s.id}?source_type=script_test`).catch(() => {})
      }
      await loadDocs()
      showToast(`${total} documentos generados`)
    } catch { showToast('Error generando scripts') }
    finally { setGenerating('') }
  }

  // ── index all
  const handleIndexAll = async () => {
    setIndexing(true)
    try {
      const r = await api.post<{ indexed: number; skipped: number; errors: number }>('/docs/index/all')
      showToast(`Indexados: ${r.data.indexed}, omitidos: ${r.data.skipped}, errores: ${r.data.errors}`)
    } catch { showToast('Error indexando documentos') }
    finally { setIndexing(false) }
  }

  // ── index single doc
  const handleIndexDoc = async () => {
    if (!selected) return
    setIndexingDoc(true)
    try {
      const r = await api.post<{ document_id: number; chunks_indexed: number }>(`/docs/${selected.id}/index`)
      setSelectedChunkCount(r.data.chunks_indexed)
      showToast(`Indexado: ${r.data.chunks_indexed} chunks`)
    } catch { showToast('Error indexando documento') }
    finally { setIndexingDoc(false) }
  }

  // ── delete
  const deleteDoc = async (doc: DocFull) => {
    if (doc.type !== 'manual') {
      showToast('Solo se pueden eliminar documentos manuales')
      return
    }
    try {
      await api.delete(`/docs/${doc.id}`)
      setSelected(null)
      setSelectedChunkCount(null)
      await loadDocs()
      showToast('Documento eliminado')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error eliminando documento'
      showToast(msg)
    }
  }

  // ── save (create/edit)
  const saveDoc = async (title: string, content: string) => {
    if (modal === 'create') {
      const r = await api.post<DocFull>('/docs', { title, content_markdown: content })
      await loadDocs()
      setSelected(r.data)
      setSelectedChunkCount(0)
    } else if (selected) {
      const r = await api.put<DocFull>(`/docs/${selected.id}`, { title, content_markdown: content })
      await loadDocs()
      setSelected(r.data)
    }
    setModal(null)
    showToast('Documento guardado')
  }

  const isIndexed = selectedChunkCount !== null && selectedChunkCount > 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '0 0 12px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)', flex: 1 }}>
            {readonly ? 'Manual del Sistema' : 'Documentación del Proyecto'}
          </h2>
          {canEdit && (
            <>
              <button onClick={() => setModal('create')} style={{ ...btnBase, background: 'var(--accent)', color: '#fff' }}>+ Doc Manual</button>
              <button onClick={genInventory} disabled={!!generating} style={{ ...btnBase, background: 'var(--bg-hover)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}>
                {generating ? generating : '⟳ Inventario'}
              </button>
              <button onClick={genAllScripts} disabled={!!generating} style={{ ...btnBase, background: 'var(--bg-hover)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}>
                {generating ? '' : '⟳ Generar scripts'}
              </button>
              <button onClick={handleIndexAll} disabled={indexing} style={{ ...btnBase, background: 'var(--bg-hover)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}>
                {indexing ? 'Indexando…' : '⟳ Indexar todo'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, display: 'flex', gap: 0, overflow: 'hidden' }}>
        {/* Left: doc list */}
        <div style={{ width: 220, flexShrink: 0, overflowY: 'auto', borderRight: '1px solid var(--border-subtle)' }}>
          {docs.length === 0 && (
            <div style={{ padding: 16, fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Sin documentos</div>
          )}
          {docs.map(d => (
            <div
              key={d.id}
              onClick={() => loadDoc(d.id)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                background: selected?.id === d.id ? 'var(--accent-subtle)' : 'transparent',
                borderLeft: selected?.id === d.id ? '3px solid var(--accent)' : '3px solid transparent',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex', alignItems: 'flex-start', gap: 8,
              }}
            >
              <span style={{ marginTop: 1, fontSize: 13 }}><TypeIcon type={d.type} /></span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: selected?.id === d.id ? 700 : 400, color: selected?.id === d.id ? 'var(--accent)' : 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {d.title}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  {new Date(d.updated_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Right: viewer */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>
          {selected ? (
            <>
              {/* Doc header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'var(--accent-subtle)', color: 'var(--accent)', fontWeight: 600, textTransform: 'uppercase' }}>
                  {selected.type === 'auto_script' ? 'Script' : selected.type === 'auto_inventory' ? 'Inventario' : 'Manual'}
                </span>
                {/* Badge de indexación */}
                {selectedChunkCount !== null && (
                  <span style={{
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 10,
                    background: isIndexed ? 'rgba(34,197,94,0.15)' : 'var(--bg-hover)',
                    color: isIndexed ? 'var(--hira-status-ok)' : 'var(--text-muted)',
                    fontWeight: 600,
                    border: `1px solid ${isIndexed ? 'var(--hira-status-ok)' : 'var(--border-default)'}`,
                  }}>
                    {isIndexed ? `✓ Indexado (${selectedChunkCount} chunks)` : 'Sin indexar'}
                  </span>
                )}
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  Actualizado: {new Date(selected.updated_at).toLocaleString()}
                </span>
                {canEdit && (
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                    <button
                      onClick={handleIndexDoc}
                      disabled={indexingDoc}
                      style={{ ...btnBase, background: 'var(--bg-hover)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
                    >
                      {indexingDoc ? 'Indexando…' : '⟳ Indexar'}
                    </button>
                    {selected.type === 'manual' && (
                      <>
                        <button onClick={() => setModal('edit')} style={{ ...btnBase, background: 'var(--bg-hover)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}>Editar</button>
                        <button onClick={() => deleteDoc(selected)} style={{ ...btnBase, background: 'var(--danger-subtle)', border: '1px solid var(--danger)', color: 'var(--danger)' }}>Eliminar</button>
                      </>
                    )}
                  </div>
                )}
              </div>
              <DocViewer content={selected.content_markdown} />
              <RAGSearchPanel />
            </>
          ) : (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 24, paddingTop: 32 }}>
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)', textAlign: 'center' }}>
                Selecciona un documento de la lista
              </div>
              <RAGSearchPanel />
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {modal && (
        <DocModal
          doc={modal === 'edit' ? selected : null}
          onSave={saveDoc}
          onClose={() => setModal(null)}
        />
      )}

      {/* Toast */}
      {toast && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', padding: '10px 16px', fontSize: 'var(--text-sm)', color: 'var(--text-primary)', boxShadow: '0 4px 12px rgba(0,0,0,0.2)', zIndex: 200 }}>
          {toast}
        </div>
      )}
    </div>
  )
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-surface)',
  border: '1px solid var(--border-default)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--text-primary)',
  padding: '7px 10px',
  fontSize: 'var(--text-sm)',
  outline: 'none',
}

const btnBase: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: 'var(--radius-md)',
  border: 'none',
  fontSize: 'var(--text-sm)',
  fontWeight: 600,
  cursor: 'pointer',
}
