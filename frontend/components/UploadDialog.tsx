'use client';

import { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import { Upload, X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  onUploaded?: () => void;
  kbId?: string;
}

export default function UploadDialog({ open, onClose, onUploaded, kbId }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [closing, setClosing] = useState(false);
  const [visible, setVisible] = useState(open);

  useEffect(() => {
    if (open) {
      setVisible(true);
      setClosing(false);
    }
  }, [open]);

  const handleClose = () => {
    setClosing(true);
    setTimeout(() => {
      setVisible(false);
      setClosing(false);
      setResult(null);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      onClose();
    }, 150);
  };

  if (!visible) return null;

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    setResult(null);
    try {
      const res = await api.upload(file, kbId, setProgress);
      setResult({ ok: true, msg: `${res.title} — 索引完成` });
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      onUploaded?.();
    } catch (err: any) {
      setResult({ ok: false, msg: err.message });
    } finally {
      setUploading(false);
    }
  };

  const bgClass = closing ? 'animate-fade-out' : 'animate-fade-in';
  const cardClass = closing ? 'animate-scale-out' : 'animate-scale-in';

  return (
    <div
      className={`fixed inset-0 bg-black/50 flex items-center justify-center z-50 ${bgClass}`}
      onClick={handleClose}
    >
      <div
        className={`bg-white rounded-xl p-6 w-full max-w-md ${cardClass}`}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold mb-4">上传文档</h2>
        <p className="text-sm text-gray-500 mb-4">
          支持 .txt / .md / .pdf / .docx / .xlsx，最大 20MB
        </p>

        <input
          ref={inputRef}
          type="file"
          accept=".txt,.md,.markdown,.pdf,.docx,.xlsx"
          onChange={(e) => {
            setFile(e.target.files?.[0] || null);
            setResult(null);
          }}
          className="w-full mb-4"
        />

        {uploading && (
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>上传中...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-200"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {result && (
          <div
            className={`mb-4 px-3 py-2 rounded-lg text-sm ${
              result.ok
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-600 border border-red-200'
            }`}
          >
            {result.msg}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            关闭
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            {uploading ? '上传中...' : '上传'}
          </button>
        </div>
      </div>
    </div>
  );
}
