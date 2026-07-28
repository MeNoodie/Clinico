import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingTimeline = ({ status }) => {
  if (!status) return null;

  return (
    <div className="flex items-center space-x-3 text-slate-500 py-2 px-4">
      <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
      <span className="text-sm font-medium animate-pulse">{status}</span>
    </div>
  );
};

export default LoadingTimeline;
