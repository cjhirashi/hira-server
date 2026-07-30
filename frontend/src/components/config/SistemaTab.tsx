import { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../../store/authStore'

interface ExportPreview {
  areas: number
  devices: number
  points: number
  logic_scripts: number
  test_scripts: number
  documents: number
  estimated_size_kb: number
}

interface ImportResult {
  imported: Record<string, number>
  skipped: Record<string, number>
  errors: string[]
}

const API = '/api/v1'

export function SistemaTab() {
  const { token } = useAuthStore()
  const [preview, setPreview] = useState<ExportPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importMode, setImportMode] = useState<'merge' | 'replace'>('merge')
  const [showConfirm, setShowConfirm] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    setPreviewLoading(true)
    fetch(`${API}/project/export/preview`, { headers })
      .then(r => r.json())
      .then(setPreview)
      .catch(() => {})
      .finally(() => setPreviewLoading(false))
  }, [])

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await fetch(`${API}/project/export`, { headers })
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `hira_project_${Date.now()}.hira`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Error al exportar: ${e}`)
    } finally {
      setExporting(false)
    }
  }

  const handleImportClick = () => {
    if (!importFile) return
    if (importMode === 'replace') {
      setShowConfirm(true)
    } else {
      doImport()
    }
  }

  const doImport = async () => {
    if (!importFile) return
    setShowConfirm(false)
    setImporting(true)
    setImportResult(null)
    setImportError(null)
    try {
      const form = new FormData()
      form.append('file', importFile)
      form.append('mode', importMode)
      form.append('confirm', importMode === 'replace' ? 'true' : 'false')
      const res = await fetch(`${API}/project/import`, {
        method: 'POST',
        headers,
        body: form,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || `${res.status}`)
      }
      const result: ImportResult = await res.json()
      setImportResult(result)
      setImportFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (e: unknown) {
      setImportError(String(e instanceof Error ? e.message : e))
    } finally {
      setImporting(false)
    }
  }

  const card: React.CSSProperties = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
    padding: '20px 24px',
    marginBottom: 20,
  }

  const label: React.CSSProperties = {
    fontSize: 'var(--text-sm)',
    color: 'var(--text-secondary)',
    marginBottom: 4,
  }

  const btn = (variant: 'primary' | 'danger' | 'ghost'): React.CSSProperties => ({
    padding: '8px 18px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 'var(--text-sm)',
    background:
      variant === 'primary' ? 'var(--accent)' :
      variant === 'danger' ? 'var(--danger)' :
      'var(--bg-hover)',
    color: variant === 'ghost' ? 'var(--text-primary)' : '#fff',
  })

  return (
    <div style={{ maxWidth: 640 }}>
      {/* Export */}
      <div style={card}>
        <h3 style={{ margin: '0 0 16px', fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>
          Backup del Proyecto
        </h3>
        {previewLoading ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Cargando resumen...</p>
        ) : preview ? (
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 24px', marginBottom: 8 }}>
              {[
                ['Áreas', preview.areas],
                ['Dispositivos', preview.devices],
                ['Puntos', preview.points],
                ['Scripts de lógica', preview.logic_scripts],
                ['Scripts de prueba', preview.test_scripts],
                ['Documentos manuales', preview.documents],
              ].map(([k, v]) => (
                <div key={String(k)}>
                  <span style={{ ...label }}>{k}: </span>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{v}</span>
                </div>
              ))}
            </div>
            <p style={{ ...label, margin: 0 }}>
              Tamaño estimado: ~{preview.estimated_size_kb} KB
            </p>
          </div>
        ) : (
          <p style={{ color: 'var(--danger)', fontSize: 'var(--text-sm)' }}>No se pudo cargar el resumen.</p>
        )}
        <button style={btn('primary')} onClick={handleExport} disabled={exporting}>
          {exporting ? 'Exportando...' : '⬇ Exportar proyecto .hira'}
        </button>
      </div>

      {/* Import */}
      <div style={card}>
        <h3 style={{ margin: '0 0 16px', fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>
          Importar Proyecto
        </h3>

        <div style={{ marginBottom: 16 }}>
          <input
            ref={fileRef}
            type="file"
            accept=".hira"
            style={{ display: 'none' }}
            onChange={e => setImportFile(e.target.files?.[0] ?? null)}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <button style={btn('ghost')} onClick={() => fileRef.current?.click()}>
              Seleccionar archivo .hira
            </button>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
              {importFile ? importFile.name : 'Ningún archivo seleccionado'}
            </span>
          </div>

          <div style={{ marginBottom: 16 }}>
            <p style={{ ...label, marginBottom: 8 }}>Modo de importación:</p>
            {(['merge', 'replace'] as const).map(m => (
              <label key={m} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="importMode"
                  value={m}
                  checked={importMode === m}
                  onChange={() => setImportMode(m)}
                />
                <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                  {m === 'merge'
                    ? 'Merge — agregar sin sobreescribir (recomendado)'
                    : 'Replace — reemplazar toda la configuración actual'}
                </span>
              </label>
            ))}
          </div>

          <button
            style={btn(importMode === 'replace' ? 'danger' : 'primary')}
            onClick={handleImportClick}
            disabled={!importFile || importing}
          >
            {importing ? 'Importando...' : '⬆ Importar'}
          </button>
        </div>

        {/* Confirm dialog para replace */}
        {showConfirm && (
          <div style={{
            background: 'var(--danger-subtle)',
            border: '1px solid var(--danger)',
            borderRadius: 'var(--radius-md)',
            padding: 16,
            marginTop: 12,
          }}>
            <p style={{ color: 'var(--danger)', fontWeight: 600, margin: '0 0 8px' }}>
              ⚠ Esta acción eliminará toda la configuración actual
            </p>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: '0 0 12px' }}>
              Áreas, dispositivos, puntos, scripts y documentos manuales serán eliminados y reemplazados
              por el contenido del archivo. Esta operación no se puede deshacer.
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button style={btn('ghost')} onClick={() => setShowConfirm(false)}>Cancelar</button>
              <button style={btn('danger')} onClick={doImport}>Confirmar e importar</button>
            </div>
          </div>
        )}

        {/* Resultado */}
        {importError && (
          <div style={{
            marginTop: 16,
            padding: 12,
            background: 'var(--danger-subtle)',
            border: '1px solid var(--danger)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-sm)',
            color: 'var(--danger)',
          }}>
            Error: {importError}
          </div>
        )}

        {importResult && (
          <div style={{
            marginTop: 16,
            padding: 16,
            background: 'var(--success-subtle)',
            border: '1px solid var(--success)',
            borderRadius: 'var(--radius-md)',
          }}>
            <p style={{ fontWeight: 600, color: 'var(--success)', margin: '0 0 8px' }}>
              ✅ Importación completada
            </p>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
              <p style={{ margin: '0 0 4px' }}>
                <strong>Insertados:</strong>{' '}
                {Object.entries(importResult.imported)
                  .filter(([, v]) => v > 0)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' · ') || 'Nada nuevo'}
              </p>
              <p style={{ margin: '0 0 4px' }}>
                <strong>Omitidos:</strong>{' '}
                {Object.entries(importResult.skipped)
                  .filter(([, v]) => v > 0)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' · ') || 'Ninguno'}
              </p>
              {importResult.errors.length > 0 && (
                <div style={{ marginTop: 8, color: 'var(--danger)' }}>
                  <strong>Errores ({importResult.errors.length}):</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
                    {importResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
