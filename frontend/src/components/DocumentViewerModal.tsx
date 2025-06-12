import React, { useEffect, useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { db } from '@/utils/db';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    docId: string;
    fileType: 'pdf' | 'image' | 'text' | 'other';
}

const DocumentViewerModal: React.FC<Props> = ({ isOpen, onClose, docId, fileType }) => {
    const [objectUrl, setObjectUrl] = useState('');
    const [text, setText] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        if (!isOpen) return;

        let url: string | null = null;

        (async () => {
            try {
                const rec = await db.docs.get(docId);
                if (!rec) throw new Error('Document not found');

                url = URL.createObjectURL(rec.blob as Blob);
                setObjectUrl(url);

                if (fileType === 'text') {
                    const content = await fetch(url).then(r => r.text());
                    setText(content);
                }
            } catch (e: any) {
                console.error(e);
                setError(e.message || 'Failed to load file');
            }
        })();

        return () => {
            if (url) URL.revokeObjectURL(url);
            setObjectUrl('');
            setText('');
            setError('');
        };
    }, [isOpen, docId, fileType]);

    useEffect(() => {
        const escHandler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', escHandler);
        return () => window.removeEventListener('keydown', escHandler);
    }, [onClose]);

    const renderContent = () => {
        if (error) return <div className="text-red-500 text-center py-4">{error}</div>;

        if (fileType === 'pdf' && objectUrl) {
            return (
                <iframe
                    src={objectUrl}
                    title="PDF Preview"
                    className="w-full h-full rounded-b-lg border-0"
                />
            );
        }

        if (fileType === 'image' && objectUrl) {
            return (
                <div className="flex justify-center items-center h-full">
                    <img
                        src={objectUrl}
                        alt="Preview"
                        className="max-h-full max-w-full object-contain rounded"
                    />
                </div>
            );
        }

        if (fileType === 'text') {
            return (
                <pre className="bg-gray-100 dark:bg-gray-900 p-6 text-sm font-mono rounded-b-lg overflow-auto h-full whitespace-pre-wrap text-gray-800 dark:text-gray-100">
                    {text || 'Loading...'}
                </pre>
            );
        }

        return (
            <div className="flex justify-center items-center h-full text-gray-500 dark:text-gray-300">
                No preview available
            </div>
        );
    };

    return (
        <Transition appear show={isOpen} as={Fragment}>
            <Dialog
                as="div"
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
                onClose={onClose}
            >
                <div className="relative w-full max-w-6xl h-[85vh] mx-4 rounded-xl overflow-hidden shadow-2xl bg-white dark:bg-gray-800 transition-all">
                    {/* Header */}
                    <div className="sticky top-0 z-10 flex items-center justify-between bg-gray-100 dark:bg-gray-700 px-6 py-4 border-b border-gray-200 dark:border-gray-600 shadow-sm">
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                            {fileType.toUpperCase()} Document Preview
                        </h3>
                        <button
                            onClick={onClose}
                            className="px-4 py-1.5 text-sm bg-gray-200 dark:bg-gray-600 text-white dark:text-white rounded hover:bg-gray-300 dark:hover:bg-gray-500 transition"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className="h-5 w-5 text-white-700 dark:text-gray-100"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                            >
                                <path
                                    fillRule="evenodd"
                                    d="M10 8.586l4.95-4.95a1 1 0 111.414 1.414L11.414 10l4.95 4.95a1 1 0 01-1.414 1.414L10 11.414l-4.95 4.95a1 1 0 01-1.414-1.414L8.586 10 3.636 5.05a1 1 0 011.414-1.414L10 8.586z"
                                    clipRule="evenodd"
                                />
                            </svg>
                        </button>
                    </div>

                    {/* Body */}
                    <div className="w-full h-[calc(100%-64px)]">{renderContent()}</div>
                </div>
            </Dialog>
        </Transition>
    );
};

export default DocumentViewerModal;
