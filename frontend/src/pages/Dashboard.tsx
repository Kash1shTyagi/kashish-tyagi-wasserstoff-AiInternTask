import QueryInput from '@/components/QueryInput';
import { useEffect, useState } from 'react';
import type { DocumentAnswer } from '../components/AnswerTable';
import AnswerTable from '../components/AnswerTable';
import type { DocumentMeta } from '../components/DocumentList';
import DocumentList from '../components/DocumentList';
import type { UploadResult } from '../components/DocumentUploader';
import DocumentUploader from '../components/DocumentUploader';
import ThemeInput from '../components/ThemeInput';
import type { ThemeItem } from '../components/ThemeSummary';
import ThemeSummary from '../components/ThemeSummary';

import DocumentViewerModal from '../components/DocumentViewerModal';

import api from '@/utils/api';
import { db } from '@/utils/db';

export default function Dashboard() {
    const [docs, setDocs] = useState<DocumentMeta[]>([]);
    const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
    const [fileMap, setFileMap] = useState<Record<string, File>>({});
    const [loadingDocs, setLoadingDocs] = useState(true);
    const [loadingQuery, setLoadingQuery] = useState(false);
    const [answers, setAnswers] = useState<DocumentAnswer[]>([]);
    const [themes, setThemes] = useState<ThemeItem[]>([]);
    const [loadingTheme, setLoadingTheme] = useState(false);

    const [viewer, setViewer] = useState<{
        isOpen: boolean;
        docId: string;
        fileType: 'pdf' | 'image' | 'text' | 'other';
    }>({
        isOpen: false,
        docId: '',
        fileType: 'other',
    });

    const loadDocs = async () => {
        setLoadingDocs(true);
        try {
            const resp = await api.get<DocumentMeta[]>('/docs');
            setDocs(resp.data);
        } catch (err) {
            console.error('Failed to load docs', err);
        } finally {
            setLoadingDocs(false);
        }
    };
    useEffect(() => { loadDocs(); }, []);

    const handleThemeFromText = async (text: string) => {
        if (!text.trim()) return;
        setLoadingTheme(true);
        try {
            const body = {
                question: text,
                top_k_per_doc: 2,
            };
            const res = await api.post('/theme', body);
            setThemes(res.data.themes);
        } catch (err) {
            console.error('Error generating themes', err);
        } finally {
            setLoadingTheme(false);
        }
    };

    const handleUploadComplete = async (results: UploadResult[]) => {
        const newDocs = results.map(r => ({
            doc_id: r.doc_id!,
            filename: r.filename,
            doc_type: r.filename.split('.').pop() || '',
            author: undefined,
            upload_date: new Date().toISOString(),
            previewUrl: r.previewUrl,
        }));
        setDocs(d => [...d, ...newDocs]);

        setFileMap(m => {
            const next = { ...m };
            results.forEach(r => { if (r.doc_id && r.file) next[r.doc_id] = r.file; });
            return next;
        });

        await Promise.all(results.map(r => {
            if (r.doc_id && r.file) {
                return db.docs.put({
                    doc_id: r.doc_id,
                    filename: r.filename,
                    blob: r.file,
                    upload_date: new Date().toISOString(),
                });
            }
        }));

        await loadDocs();
    };

    const handleDelete = async (docId: string) => {
        if (!confirm('Delete this document?')) return;
        try {
            await api.delete(`/docs/${docId}`);
            setFileMap(m => {
                const { [docId]: _, ...rest } = m;
                return rest;
            });
            setDocs(prev => prev.filter(d => d.doc_id !== docId));
        } catch (err: any) {
            console.error('Error deleting document:', err);
            alert('Error deleting document: ' + (err.response?.data?.detail || 'Deletion failed'));
        }
    };

    const openPreview = async (doc: DocumentMeta) => {
        const ext = doc.filename.split('.').pop()?.toLowerCase();
        let ft: typeof viewer.fileType = 'other';
        if (ext === 'pdf') ft = 'pdf';
        else if (['png', 'jpg', 'jpeg', 'gif', 'bmp'].includes(ext || '')) ft = 'image';
        else if (ext === 'txt') ft = 'text';

        if (!fileMap[doc.doc_id]) {
            const rec = await db.docs.get(doc.doc_id);
            if (rec?.blob) {
                setFileMap(m => ({ ...m, [doc.doc_id]: rec.blob as File }));
            }
        }

        setViewer({ isOpen: true, docId: doc.doc_id, fileType: ft });
    };

    const closeViewer = () => setViewer(v => ({ ...v, isOpen: false }));

    return (
        <div className="min-h-screen p-6 grid grid-cols-4 gap-6">
            <aside className="space-y-6">
                <DocumentUploader onUploadComplete={handleUploadComplete} />
                {loadingDocs
                    ? <div>Loading…</div>
                    : docs.length === 0
                        ? <div>No docs</div>
                        : <DocumentList
                            docs={docs}
                            onSelectionChange={setSelectedDocIds}
                            onDelete={handleDelete}
                        />
                }
                <button
                    onClick={() => {
                        const sel = docs.find(d => d.doc_id === selectedDocIds[0]);
                        if (sel) openPreview(sel);
                    }}
                    disabled={selectedDocIds.length !== 1}
                    className="w-full py-2 bg-blue-600 text-white rounded disabled:opacity-50"
                >
                    Preview Selected Doc
                </button>
            </aside>

            <main className="col-span-3 space-y-6">
                <QueryInput
                    loading={loadingQuery}
                    setLoading={setLoadingQuery}
                    onResponse={(data) => {
                        setAnswers(data?.individual_answers || []);
                    }}
                />
                <section>
                    <h2 className="text-lg font-semibold">Document Answers</h2>
                    {loadingQuery
                        ? <div>Running query…</div>
                        : answers.length
                            ? <AnswerTable data={answers} />
                            : <div>No answers to show.</div>
                    }
                </section>
                <ThemeInput onSubmit={handleThemeFromText} loading={loadingTheme} />
                <section>
                    <h2 className="text-lg font-semibold">Themes Summary</h2>
                    {loadingTheme
                        ? <div>Generating themes…</div>
                        : themes.length
                            ? <ThemeSummary themes={themes} />
                            : <div>No themes to show.</div>
                    }
                </section>
            </main>

            {viewer.isOpen && (
                <DocumentViewerModal
                    isOpen={viewer.isOpen}
                    onClose={closeViewer}
                    docId={viewer.docId}
                    fileType={viewer.fileType}
                />
            )}
        </div>
    );
}
