'use client'

import { Suspense, useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { useRouter, useSearchParams } from 'next/navigation'

export default function NewPostPage() {
  return (
    <Suspense fallback={null}>
      <NewPostForm />
    </Suspense>
  )
}

const PLATFORM_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  twitter: 'Twitter / X',
  blog: 'Blog',
}

const PLATFORM_LIMITS: Record<string, number> = {
  linkedin: 1300,
  twitter: 280,
  blog: 3000,
}

type PlatformResult = {
  postId: number | null
  content: string
  error: string | null
  saving: boolean
  saved: boolean
  previousContent: string | null
  applyingCommand: string | null
}

type ArticleInfo = {
  title: string
  url: string
  source_name: string
}

const AI_COMMANDS: { value: string; label: string }[] = [
  { value: 'shorten', label: 'Raccourcir' },
  { value: 'expand', label: 'Développer' },
  { value: 'tone:formal', label: 'Ton formel' },
  { value: 'tone:casual', label: 'Ton décontracté' },
  { value: 'angle:question', label: 'Hook → question' },
  { value: 'angle:stat', label: 'Hook → stat' },
  { value: 'hashtags', label: '+ Hashtags' },
]

function NewPostForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const articleIdFromUrl = searchParams.get('article_id')
  const edit_id = searchParams.get('edit_id')
  const isEditing = Boolean(edit_id)

  // --- Source de génération : article existant, ou PDF/texte ingéré (SCRUM-35) ---
  const [inputMode, setInputMode] = useState<'article' | 'upload'>(articleIdFromUrl ? 'article' : 'upload')
  const [article_id, setArticleId] = useState<string | null>(articleIdFromUrl)
  const [uploadText, setUploadText] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [ingesting, setIngesting] = useState(false)
  const [ingestPreview, setIngestPreview] = useState<string | null>(null)
  const [ingestError, setIngestError] = useState('')

  async function handleIngest() {
    if (!uploadFile && !uploadText.trim()) return
    setIngesting(true)
    setIngestError('')
    try {
      const token = getToken()
      let response
      if (uploadFile) {
        const formData = new FormData()
        formData.append('file', uploadFile)
        response = await apiFetch('/posts/ingest/', token, { method: 'POST', body: formData })
      } else {
        response = await apiFetch('/posts/ingest/', token, {
          method: 'POST',
          body: JSON.stringify({ text: uploadText.trim() }),
        })
      }
      setArticleId(String(response.id))
      setIngestPreview(response.content)
    } catch {
      setIngestError('Impossible de traiter ce fichier ou ce texte (PDF illisible, trop volumineux, ou texte trop long).')
    }
    setIngesting(false)
  }

  // --- Mode édition d'un brouillon existant (post unique) ---
  const [editPostId, setEditPostId] = useState<number | null>(null)
  const [editContent, setEditContent] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [editPreviousContent, setEditPreviousContent] = useState<string | null>(null)
  const [editApplyingCommand, setEditApplyingCommand] = useState<string | null>(null)

  async function handleEditAiCommand(command: string) {
    if (!editPostId) return
    setEditApplyingCommand(command)
    try {
      const token = getToken()
      const response = await apiFetch(`/posts/${editPostId}/ai-command/`, token, {
        method: 'POST',
        body: JSON.stringify({ command }),
      })
      setEditPreviousContent(editContent)
      setEditContent(response.content)
    } catch {
      alert('Erreur lors de l\'exécution de la commande /ai')
    }
    setEditApplyingCommand(null)
  }

  function handleUndoEditCommand() {
    if (editPreviousContent === null) return
    setEditContent(editPreviousContent)
    setEditPreviousContent(null)
  }

  useEffect(() => {
    if (!edit_id) return
    const token = getToken()
    apiFetch(`/posts/${edit_id}/`, token)
      .then(post => {
        setEditPostId(post.id)
        setEditContent(post.content)
      })
      .catch(() => alert('Post introuvable'))
  }, [edit_id])

  async function handleSaveEdit() {
    if (!editPostId) return
    setEditSaving(true)
    try {
      const token = getToken()
      await apiFetch(`/posts/${editPostId}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ content: editContent }),
      })
      router.push('/posts')
    } catch {
      alert('Erreur lors de la sauvegarde')
      setEditSaving(false)
    }
  }

  // --- Mode génération (multi-plateforme) ---
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['linkedin'])
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<Record<string, PlatformResult>>({})
  const [activeTab, setActiveTab] = useState<string | null>(null)

  // --- Widget sources et citations (SCRUM-33, 100% client-side) ---
  const [articleInfo, setArticleInfo] = useState<ArticleInfo | null>(null)
  const [sourcesPanelOpen, setSourcesPanelOpen] = useState(true)
  const [citationText, setCitationText] = useState('')

  useEffect(() => {
    if (!article_id) return
    const token = getToken()
    apiFetch(`/articles/${article_id}/`, token)
      .then(article => setArticleInfo({
        title: article.title, url: article.url, source_name: article.source_name,
      }))
      .catch(() => setArticleInfo(null))
  }, [article_id])

  function insertIntoActiveTab(text: string) {
    if (!activeTab) return
    setResults(prev => ({
      ...prev,
      [activeTab]: { ...prev[activeTab], content: `${prev[activeTab].content}\n\n${text}` },
    }))
  }

  function handleInsertSource() {
    if (!articleInfo) return
    insertIntoActiveTab(`Source : ${articleInfo.source_name} — ${articleInfo.url}`)
  }

  function handleInsertCitation() {
    if (!articleInfo || !citationText.trim()) return
    insertIntoActiveTab(`"${citationText.trim()}" — ${articleInfo.source_name}`)
    setCitationText('')
  }

  function togglePlatform(platform: string) {
    setSelectedPlatforms(prev =>
      prev.includes(platform) ? prev.filter(p => p !== platform) : [...prev, platform]
    )
  }

  async function handleGenerate() {
    if (selectedPlatforms.length === 0) return
    setLoading(true)
    try {
      const token = getToken()
      const response = await apiFetch('/posts/generate-multi/', token, {
        method: 'POST',
        body: JSON.stringify({ article_id, platforms: selectedPlatforms }),
      })
      const nextResults: Record<string, PlatformResult> = {}
      for (const r of response.results) {
        nextResults[r.platform] = {
          postId: r.id ?? null,
          content: r.content ?? '',
          error: r.error ?? null,
          saving: false,
          saved: false,
          previousContent: null,
          applyingCommand: null,
        }
      }
      setResults(nextResults)
      setActiveTab(selectedPlatforms[0])
    } catch {
      alert('Erreur lors de la generation')
    }
    setLoading(false)
  }

  function updateResultContent(platform: string, content: string) {
    setResults(prev => ({ ...prev, [platform]: { ...prev[platform], content } }))
  }

  async function handleAiCommand(platform: string, command: string) {
    const result = results[platform]
    if (!result?.postId) return
    setResults(prev => ({ ...prev, [platform]: { ...prev[platform], applyingCommand: command } }))
    try {
      const token = getToken()
      const response = await apiFetch(`/posts/${result.postId}/ai-command/`, token, {
        method: 'POST',
        body: JSON.stringify({ command }),
      })
      setResults(prev => ({
        ...prev,
        [platform]: {
          ...prev[platform],
          previousContent: prev[platform].content,
          content: response.content,
          applyingCommand: null,
        },
      }))
    } catch {
      alert('Erreur lors de l\'exécution de la commande /ai')
      setResults(prev => ({ ...prev, [platform]: { ...prev[platform], applyingCommand: null } }))
    }
  }

  function handleUndoCommand(platform: string) {
    const result = results[platform]
    if (!result || result.previousContent === null) return
    setResults(prev => ({
      ...prev,
      [platform]: { ...prev[platform], content: result.previousContent!, previousContent: null },
    }))
  }

  async function handleSaveOne(platform: string) {
    const result = results[platform]
    if (!result?.postId) return
    setResults(prev => ({ ...prev, [platform]: { ...prev[platform], saving: true } }))
    try {
      const token = getToken()
      await apiFetch(`/posts/${result.postId}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ content: result.content }),
      })
      setResults(prev => ({ ...prev, [platform]: { ...prev[platform], saving: false, saved: true } }))
    } catch {
      alert(`Erreur lors de la sauvegarde (${PLATFORM_LABELS[platform]})`)
      setResults(prev => ({ ...prev, [platform]: { ...prev[platform], saving: false } }))
    }
  }

  async function handleSaveAll() {
    const platforms = Object.keys(results).filter(p => results[p].postId)
    await Promise.all(platforms.map(handleSaveOne))
    router.push('/posts')
  }

  const generatedPlatforms = Object.keys(results)

  if (isEditing) {
    return (
      <div className="flex flex-col gap-8 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Modifier le post</h1>
          <p className="text-gray-500 mt-1">Modifie le contenu puis sauvegarde</p>
        </div>
        <div className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
          <textarea
            value={editContent}
            onChange={e => setEditContent(e.target.value)}
            rows={10}
            className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500">Commandes /ai</span>
              {editPreviousContent !== null && (
                <button
                  onClick={handleUndoEditCommand}
                  className="text-xs text-indigo-600 hover:underline"
                >
                  ↺ Annuler la dernière commande
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {AI_COMMANDS.map(cmd => (
                <button
                  key={cmd.value}
                  onClick={() => handleEditAiCommand(cmd.value)}
                  disabled={editApplyingCommand !== null}
                  className="text-xs bg-gray-50 text-gray-600 border border-gray-200 rounded-full px-3 py-1 hover:bg-gray-100 transition disabled:opacity-50"
                >
                  {editApplyingCommand === cmd.value ? '…' : cmd.label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleSaveEdit}
            disabled={editSaving}
            className="bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {editSaving ? 'Sauvegarde...' : 'Sauvegarder et voir mes posts'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-start max-w-5xl">
    <div className="flex flex-col gap-8 max-w-2xl w-full">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Generer un post</h1>
        <p className="text-gray-500 mt-1">Klark va transformer l&apos;article en post pret a publier</p>
      </div>

      <div className="flex gap-2 border-b border-gray-100">
        {articleIdFromUrl && (
          <button
            onClick={() => setInputMode('article')}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              inputMode === 'article'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Depuis l&apos;article
          </button>
        )}
        <button
          onClick={() => setInputMode('upload')}
          className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition ${
            inputMode === 'upload'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Depuis un PDF ou texte
        </button>
      </div>

      {inputMode === 'upload' && (
        <div className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Fichier PDF (max 10 Mo)</label>
            <input
              type="file"
              accept="application/pdf"
              onChange={e => {
                setUploadFile(e.target.files?.[0] ?? null)
                setUploadText('')
              }}
              className="w-full text-sm"
            />
          </div>
          <p className="text-center text-xs text-gray-400">— ou —</p>
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">
              Transcription (texte libre, max 10 000 caractères)
            </label>
            <textarea
              value={uploadText}
              onChange={e => {
                setUploadText(e.target.value.slice(0, 10_000))
                setUploadFile(null)
              }}
              rows={6}
              placeholder="Colle ici la transcription d'une conférence, un rapport..."
              className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
            <p className="text-xs text-gray-400 mt-1">{uploadText.length} / 10 000 caractères</p>
          </div>

          {ingestError && <p className="text-sm text-red-500">{ingestError}</p>}

          <button
            onClick={handleIngest}
            disabled={ingesting || (!uploadFile && !uploadText.trim())}
            className="bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {ingesting ? 'Extraction en cours...' : 'Extraire le texte'}
          </button>

          {ingestPreview && (
            <div className="border border-gray-200 rounded-lg p-3 max-h-40 overflow-y-auto">
              <p className="text-xs font-medium text-gray-500 mb-1">Texte extrait (aperçu) :</p>
              <p className="text-xs text-gray-600 whitespace-pre-wrap">{ingestPreview}</p>
            </div>
          )}
        </div>
      )}

      <div className="bg-white rounded-xl p-6 border border-gray-100 flex flex-col gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Plateformes</label>
          <div className="flex gap-2">
            {Object.keys(PLATFORM_LABELS).map(platform => (
              <label
                key={platform}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm cursor-pointer transition ${
                  selectedPlatforms.includes(platform)
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 text-gray-600 hover:border-indigo-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedPlatforms.includes(platform)}
                  onChange={() => togglePlatform(platform)}
                  className="accent-indigo-600"
                />
                {PLATFORM_LABELS[platform]}
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || selectedPlatforms.length === 0 || !article_id}
          className="bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          {loading ? 'Generation en cours...' : 'Generer avec Klark'}
        </button>
      </div>

      {generatedPlatforms.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 flex flex-col">
          <div className="flex border-b border-gray-100">
            {generatedPlatforms.map(platform => (
              <button
                key={platform}
                onClick={() => setActiveTab(platform)}
                className={`px-4 py-3 text-sm font-medium border-b-2 -mb-px transition ${
                  activeTab === platform
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {PLATFORM_LABELS[platform]}
                {results[platform].error && ' ⚠️'}
              </button>
            ))}
          </div>

          {activeTab && results[activeTab] && (
            <div className="p-6 flex flex-col gap-4">
              {results[activeTab].error ? (
                <p className="text-sm text-red-500">
                  Erreur lors de la génération pour {PLATFORM_LABELS[activeTab]} : {results[activeTab].error}
                </p>
              ) : (
                <>
                  <textarea
                    value={results[activeTab].content}
                    onChange={e => updateResultContent(activeTab, e.target.value)}
                    rows={10}
                    className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  />
                  <div className="flex items-center justify-between text-xs">
                    <span className={
                      results[activeTab].content.length > PLATFORM_LIMITS[activeTab]
                        ? 'text-red-500 font-medium'
                        : 'text-gray-400'
                    }>
                      {results[activeTab].content.length} / {PLATFORM_LIMITS[activeTab]} caractères
                    </span>
                  </div>

                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-gray-500">Commandes /ai</span>
                      {results[activeTab].previousContent !== null && (
                        <button
                          onClick={() => handleUndoCommand(activeTab)}
                          className="text-xs text-indigo-600 hover:underline"
                        >
                          ↺ Annuler la dernière commande
                        </button>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {AI_COMMANDS.map(cmd => (
                        <button
                          key={cmd.value}
                          onClick={() => handleAiCommand(activeTab, cmd.value)}
                          disabled={results[activeTab].applyingCommand !== null}
                          className="text-xs bg-gray-50 text-gray-600 border border-gray-200 rounded-full px-3 py-1 hover:bg-gray-100 transition disabled:opacity-50"
                        >
                          {results[activeTab].applyingCommand === cmd.value ? '…' : cmd.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => handleSaveOne(activeTab)}
                      disabled={results[activeTab].saving}
                      className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
                    >
                      {results[activeTab].saved
                        ? 'Enregistré ✓'
                        : results[activeTab].saving
                          ? 'Sauvegarde...'
                          : 'Sauvegarder cette version'}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          <div className="p-6 pt-0">
            <button
              onClick={handleSaveAll}
              className="w-full border border-gray-200 text-gray-600 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
            >
              Tout sauvegarder et voir mes posts
            </button>
          </div>
        </div>
      )}
    </div>

    {articleInfo && (
      <div className="w-full lg:w-72 shrink-0 bg-white rounded-xl border border-gray-100 flex flex-col gap-4 p-5">
        <button
          onClick={() => setSourcesPanelOpen(o => !o)}
          className="flex items-center justify-between text-sm font-semibold text-gray-900"
        >
          Sources & citations
          <span className="text-gray-400">{sourcesPanelOpen ? '−' : '+'}</span>
        </button>

        {sourcesPanelOpen && (
          <>
            <div className="flex flex-col gap-1">
              <a
                href={articleInfo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-indigo-600 hover:underline"
              >
                {articleInfo.title}
              </a>
              {articleInfo.source_name && (
                <p className="text-xs text-gray-400">{articleInfo.source_name}</p>
              )}
            </div>

            <button
              onClick={handleInsertSource}
              disabled={!activeTab}
              className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg px-3 py-2 hover:bg-indigo-100 transition disabled:opacity-50"
            >
              Insérer la source
            </button>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-gray-700">Citation (max 150 car.)</label>
              <textarea
                value={citationText}
                onChange={e => setCitationText(e.target.value.slice(0, 150))}
                rows={3}
                placeholder="Extrait à citer..."
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              />
              <button
                onClick={handleInsertCitation}
                disabled={!activeTab || !citationText.trim()}
                className="text-xs bg-gray-50 text-gray-700 border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-100 transition disabled:opacity-50"
              >
                Insérer la citation
              </button>
            </div>
          </>
        )}
      </div>
    )}
    </div>
  )
}
