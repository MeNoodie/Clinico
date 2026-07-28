import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, ShieldCheck, Clock, FileText } from 'lucide-react';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)]">
      <main className="flex-grow flex items-center justify-center bg-slate-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex justify-center mb-8">
            <div className="bg-primary-100 p-4 rounded-full">
              <Activity className="h-16 w-16 text-primary-600" />
            </div>
          </div>
          <h1 className="text-5xl font-extrabold text-slate-900 tracking-tight mb-4">
            Next-Generation Healthcare Administration
          </h1>
          <p className="text-xl text-slate-600 mb-8 max-w-2xl mx-auto">
            AgentCare uses advanced AI to seamlessly handle your appointments, 
            documents, and patient history in one secure platform.
          </p>
          
          <div className="flex justify-center mb-16">
            <button
              onClick={() => navigate('/dashboard')}
              className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-full shadow-sm text-white bg-primary-600 hover:bg-primary-700 transition-colors"
            >
              Get Started
              <ArrowRight className="ml-2 h-5 w-5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <Clock className="h-8 w-8 text-primary-500 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Smart Scheduling</h3>
              <p className="text-slate-600">AI-driven booking and rescheduling that understands your needs.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <ShieldCheck className="h-8 w-8 text-primary-500 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Secure & Private</h3>
              <p className="text-slate-600">Built-in safety agents ensure all data and interactions are protected.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <FileText className="h-8 w-8 text-primary-500 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Document Analysis</h3>
              <p className="text-slate-600">Easily upload and manage your health records in one place.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Landing;
