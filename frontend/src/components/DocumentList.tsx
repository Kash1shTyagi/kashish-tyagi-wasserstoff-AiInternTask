import { useEffect, useState } from 'react';

export interface DocumentMeta {
    doc_id: string;
    filename: string;
    doc_type: string;
    author?: string;
    upload_date: string;
    previewUrl?: string;
}

interface DocumentListProps {
    docs: DocumentMeta[];
    onSelectionChange: (ids: string[]) => void;
    onDelete: (docId: string) => void | Promise<void>;
}

export default function DocumentList({
    docs,
    onSelectionChange,
    onDelete,
}: DocumentListProps) {
    const [filtered, setFiltered] = useState<DocumentMeta[]>(docs);
    const [search, setSearch] = useState('');
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    useEffect(() => {
        setFiltered(docs);
        setSelectedIds(new Set());
        onSelectionChange([]);
    }, [docs, onSelectionChange]);

    useEffect(() => {
        const q = search.toLowerCase();
        setFiltered(
            docs.filter(d =>
                d.filename.toLowerCase().includes(q) ||
                d.doc_type.toLowerCase().includes(q) ||
                (d.author?.toLowerCase().includes(q) ?? false)
            )
        );
    }, [search, docs]);

    const toggleSelect = (docId: string) => {
        const next = new Set(selectedIds);
        if (next.has(docId)) next.delete(docId);
        else next.add(docId);
        setSelectedIds(next);
        onSelectionChange(Array.from(next));
    };

    const handleDelete = (docId: string) => {
        console.log('[DocumentList] delete requested for:', docId);
        onDelete(docId);
    };

    return (
        <div>
            <input
                className="w-full p-2 border rounded mb-2"
                placeholder="Search…"
                value={search}
                onChange={e => setSearch(e.target.value)}
            />

            <ul className="space-y-2 max-h-64 overflow-y-auto">
                {filtered.map(d => (
                    <li
                        key={d.doc_id}
                        className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded"
                    >
                        <div className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                checked={selectedIds.has(d.doc_id)}
                                onChange={() => toggleSelect(d.doc_id)}
                            />
                            <div>
                                <p className="font-medium text-gray-800 dark:text-gray-100">{d.filename}</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {d.doc_type.toUpperCase()} • {new Date(d.upload_date).toLocaleDateString()}
                                </p>
                            </div>
                        </div>

                        <button
                            onClick={() => handleDelete(d.doc_id)}
                            className="text-white hover:text-white p-2 rounded-full hover:bg-red-100 dark:hover:bg-red-800 dark:text-red-400 transition"
                            title="Delete"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className="h-5 w-5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </li>
                ))}

                {filtered.length === 0 && (
                    <li className="text-center text-gray-500 dark:text-gray-400">No documents found.</li>
                )}
            </ul>
        </div>
    );
}
