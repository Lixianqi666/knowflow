'use client';

import { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import { Upload, File, X } from 'lucide-react';

interface Props { open: boolean; onClose: () => void; onUploaded?: () => void; kbId?: string; }

export default function UploadDialog({ open, onClose, onUploaded, kbId }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [closing, setClosing] = useState(false);
  const [visible, setVisible] = useState(open);

  useEffect(() => { if (open) { setVisible(true); setClosing(false); } }, [open]);

  const handleClose = () => {
    setClosing(true);
    setTimeout(() => { setVisible(false); setClosing(false); setResult(null); setFile(null); if (inputRef.current) inputRef.current.value = ''; onClose(); }, 150);
  };

  if (!visible) return null;

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setProgress(0); setResult(null);
    try {
      const res = await api.upload(file, kbId, setProgress);
      setResult({ ok: true, msg: `${res.title} — 已加入索引队列` }); setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      onUploaded?.();
    } catch (err: any) { setResult({ ok: false, msg: err.message }); }
    finally { setUploading(false); }
  };

  const bgClass = closing ? 'animate-fade-out' : 'animate-fade-in';
  const cardClass = closing ? 'animate-scale-out' : 'animate-scale-in';

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center ${bgClass}`}
      style={{ background: 'rgba(15,23,42,.45)', backdropFilter: 'blur(4px)' }} onClick={handleClose}>
      <div className={`bg-white rounded-2xl p-6 w-full max-w-md mx-4 ${cardClass}`}
        style={{ boxShadow: 'var(--shadow-lg)' }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold tracking-tight">上传文档</h2>
          <button onClick={handleClose} className="p-1.5 rounded-lg transition-colors border-none cursor-pointer"
            style={{ color: 'var(--c-text-tertiary)', background: 'none' }}><X className="w-5 h-5" /></button>
        </div>
        <p className="text-sm mb-5" style={{ color: 'var(--c-text-secondary)' }}>支持 .txt / .md / .pdf / .docx / .xlsx，最大 20MB</p>

        <label className="flex flex-col items-center justify-center gap-3 px-4 py-8 rounded-xl border-2 border-dashed cursor-pointer transition-all mb-4"
          style={{ borderColor: file ? 'var(--c-primary)' : 'var(--c-border)', background: file ? 'var(--c-primary-subtle)' : 'var(--c-bg)' }}>
          {file ? (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}><File className="w-5 h-5" /></div>
              <div><p className="text-sm font-medium">{file.name}</p><p className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>{(file.size / 1024).toFixed(1)} KB</p></div>
            </div>
          ) : (
            <>
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}><Upload className="w-6 h-6" /></div>
              <div className="text-center"><p className="text-sm font-medium">点击选择文件或拖拽到此处</p><p className="text-xs mt-1" style={{ color: 'var(--c-text-tertiary)' }}>txt / md / pdf / docx / xlsx</p></div>
            </>
          )}
          <input ref={inputRef} type="file" accept=".txt,.md,.markdown,.pdf,.docx,.xlsx" onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); }} className="hidden" />
        </label>

        {uploading && (
          <div className="mb-4">
            <div className="flex justify-between text-xs mb-1" style={{ color: 'var(--c-text-tertiary)' }}><span>上传中...</span><span>{progress}%</span></div>
            <div className="w-full rounded-full h-2" style={{ background: 'var(--c-skeleton)' }}><div className="h-2 rounded-full transition-all duration-300 ease-out" style={{ width: `${progress}%`, background: 'var(--c-primary)' }} /></div>
          </div>
        )}

        {result && (
          <div className={`mb-4 px-4 py-2.5 rounded-xl text-sm flex items-center gap-2 ${result.ok ? 'bg-green-50 text-green-700 border border-green-200/50' : 'bg-red-50 text-red-600 border border-red-200/50'}`}>
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${result.ok ? 'bg-green-500' : 'bg-red-500'}`} />{result.msg}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button onClick={handleClose} className="px-4 py-2 rounded-xl text-sm font-medium transition-all border-none cursor-pointer" style={{ color: 'var(--c-text-secondary)', background: 'transparent' }}>取消</button>
          <button onClick={handleUpload} disabled={!file || uploading} className="btn-primary px-5"><Upload className="w-4 h-4" />{uploading ? '上传中...' : '上传'}</button>
        </div>
      </div>
    </div>
  );
}
