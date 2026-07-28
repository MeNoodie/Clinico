import React from 'react';
import { Upload, File } from 'lucide-react';

const Documents = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Medical Documents</h1>
      
      <div className="bg-white border-2 border-dashed border-slate-300 rounded-2xl p-12 text-center hover:border-primary-400 hover:bg-slate-50 transition-colors cursor-pointer mb-8">
        <div className="flex justify-center mb-4">
          <div className="bg-primary-50 p-4 rounded-full">
            <Upload className="h-8 w-8 text-primary-500" />
          </div>
        </div>
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Upload Document</h3>
        <p className="text-slate-500 mb-4">Drag and drop your files here, or click to browse</p>
        <p className="text-xs text-slate-400">Supports PDF, JPG, PNG (Max 10MB)</p>
      </div>

      <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center">
        <File className="mr-2 h-5 w-5 text-slate-400" />
        Recent Uploads
      </h2>
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 text-center text-slate-500">
        No documents uploaded yet.
      </div>
    </div>
  );
};

export default Documents;
