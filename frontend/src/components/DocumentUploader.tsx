import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import api from '@/utils/api';
import { Button } from '@/components/ui/button';
import { toast } from 'react-hot-toast';

export interface UploadResult {
    doc_id?: string;
    filename: string;
    status: 'indexed' | 'error' | 'skipped';
    detail?: string;
    previewUrl?: string;
    file?: File;
}

interface DocumentUploaderProps {
    onUploadComplete?: (results: UploadResult[]) => void;
}

export default function DocumentUploader({ onUploadComplete }: DocumentUploaderProps) {
    const [uploading, setUploading] = useState(false);
    const [files, setFiles] = useState<File[]>([]);

    const onDrop = useCallback((accepted: File[]) => {
        setFiles(prev => [...prev, ...accepted]);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'], 'image/png': ['.png'], 'image/jpeg': ['.jpg', '.jpeg'] },
        multiple: true,
    });

    const handleUpload = async () => {
        if (files.length === 0) return;
        setUploading(true);

        const formData = new FormData();
        files.forEach(f => formData.append('files', f));

        try {
            const resp = await api.post<{ upload_results: Omit<UploadResult, 'file' | 'previewUrl'>[] }>(
                '/upload',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );
            const serverResults = resp.data.upload_results;
            console.log("Server Result: ", serverResults)
            const detailed: UploadResult[] = serverResults.map(r => {
                const matchFile = files.find(f => f.name === r.filename);
                const previewUrl = matchFile ? URL.createObjectURL(matchFile) : undefined;
                return { ...r, file: matchFile, previewUrl };
            });
            toast.success('Upload completed!');
            onUploadComplete?.(detailed);
            setFiles([]);
        } catch (err) {
            console.error('Upload error', err);
            toast.error('Upload failed.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="border-2 border-dashed border-gray-300 p-6 rounded-lg bg-white">
            <div
                {...getRootProps()}
                className={`cursor-pointer p-6 text-center ${isDragActive ? 'bg-gray-100' : ''}`}
            >
                <input {...getInputProps()} />
                {isDragActive ? <p>Drop the files here...</p> : <p>Drag & drop documents here, or click to select files</p>}
            </div>

            {files.length > 0 && (
                <div className="mt-4">
                    <h4 className="font-medium mb-2">Pending Uploads:</h4>
                    <ul className="list-disc ml-5 mb-4">
                        {files.map((file, idx) => <li key={idx} className="text-sm">{file.name}</li>)}
                    </ul>
                    <Button onClick={handleUpload} disabled={uploading}>{uploading ? 'Uploading...' : 'Start Upload'}</Button>
                </div>
            )}
        </div>
    );
}

