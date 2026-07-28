import React from 'react';
import { Calendar } from 'lucide-react';

const History = () => {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Appointment History</h1>
      
      <div className="space-y-8">
        <section>
          <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center">
            <Calendar className="mr-2 h-5 w-5 text-primary-500" />
            Upcoming Appointments
          </h2>
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 text-center text-slate-500">
            No upcoming appointments found.
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center">
            <Calendar className="mr-2 h-5 w-5 text-slate-400" />
            Past Appointments
          </h2>
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 text-center text-slate-500">
            No past appointments found.
          </div>
        </section>
      </div>
    </div>
  );
};

export default History;
