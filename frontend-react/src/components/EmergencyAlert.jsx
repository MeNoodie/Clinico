import React from 'react';
import { AlertTriangle } from 'lucide-react';

const EmergencyAlert = ({ message }) => {
  return (
    <div className="bg-red-50 border-l-4 border-red-500 rounded-r-xl shadow-sm p-4 my-4 max-w-sm">
      <div className="flex">
        <div className="flex-shrink-0">
          <AlertTriangle className="h-6 w-6 text-red-500" />
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">Medical Emergency</h3>
          <div className="mt-2 text-sm text-red-700">
            <p>{message || 'Please contact emergency medical services immediately.'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmergencyAlert;
