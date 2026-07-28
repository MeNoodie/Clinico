import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarPlus, CalendarMinus, CalendarClock, Activity, UploadCloud } from 'lucide-react';

const Dashboard = () => {
  const navigate = useNavigate();

  const handleWorkflowClick = (intent) => {
    navigate('/chat', { state: { intent } });
  };

  const workflows = [
    {
      title: 'Book Appointment',
      description: 'Schedule a new visit with a doctor.',
      icon: <CalendarPlus className="h-8 w-8 text-blue-500" />,
      intent: 'BOOK_APPOINTMENT',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Reschedule Appointment',
      description: 'Change the time of an existing appointment.',
      icon: <CalendarClock className="h-8 w-8 text-orange-500" />,
      intent: 'RESCHEDULE_APPOINTMENT',
      bgColor: 'bg-orange-50',
    },
    {
      title: 'Cancel Appointment',
      description: 'Cancel an upcoming visit.',
      icon: <CalendarMinus className="h-8 w-8 text-red-500" />,
      intent: 'CANCEL_APPOINTMENT',
      bgColor: 'bg-red-50',
    },
    {
      title: 'Follow-up Appointment',
      description: 'Book a follow-up after a recent visit.',
      icon: <Activity className="h-8 w-8 text-green-500" />,
      intent: 'FOLLOWUP_APPOINTMENT',
      bgColor: 'bg-green-50',
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Patient Dashboard</h1>
        <p className="text-slate-600">Select a workflow to get started with AgentCare.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {workflows.map((wf) => (
          <button
            key={wf.title}
            onClick={() => handleWorkflowClick(wf.intent)}
            className="flex flex-col items-center text-center p-8 bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md hover:border-primary-200 transition-all cursor-pointer group"
          >
            <div className={`p-4 rounded-full ${wf.bgColor} mb-4 group-hover:scale-110 transition-transform`}>
              {wf.icon}
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-2">{wf.title}</h3>
            <p className="text-slate-500 text-sm">{wf.description}</p>
          </button>
        ))}

        <button
          onClick={() => handleWorkflowClick('UPLOAD_DOCUMENT')}
          className="flex flex-col items-center text-center p-8 bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md hover:border-primary-200 transition-all cursor-pointer group"
        >
          <div className="p-4 rounded-full bg-purple-50 mb-4 group-hover:scale-110 transition-transform">
            <UploadCloud className="h-8 w-8 text-purple-500" />
          </div>
          <h3 className="text-xl font-semibold text-slate-900 mb-2">Upload Documents</h3>
          <p className="text-slate-500 text-sm">Upload test reports and medical records.</p>
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
