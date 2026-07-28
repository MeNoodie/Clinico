import React from 'react';
import { CalendarCheck, Clock, User, Building } from 'lucide-react';

const AppointmentCard = ({ appointment }) => {
  if (!appointment) return null;

  const date = appointment.booked_datetime ? new Date(appointment.booked_datetime) : new Date();
  
  const formattedDate = date.toLocaleDateString('en-US', { day: 'numeric', month: 'long' });
  const formattedTime = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-100 overflow-hidden my-4 max-w-sm">
      <div className="bg-blue-500 px-4 py-3 flex items-center justify-between">
        <h3 className="text-white font-medium flex items-center">
          <CalendarCheck className="h-5 w-5 mr-2" />
          Appointment Confirmed
        </h3>
        <span className="text-blue-100 text-xs">ID: {appointment.appointment_id || 'N/A'}</span>
      </div>
      <div className="p-4 space-y-3">
        <div className="flex items-start">
          <Building className="h-5 w-5 text-slate-400 mr-3 mt-0.5" />
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider">Department</p>
            <p className="font-medium text-slate-900">{appointment.department || 'General'}</p>
          </div>
        </div>
        
        <div className="flex items-start">
          <User className="h-5 w-5 text-slate-400 mr-3 mt-0.5" />
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider">Doctor</p>
            <p className="font-medium text-slate-900">{appointment.doctor || 'Dr. Sharma'}</p>
          </div>
        </div>

        <div className="flex items-start">
          <Clock className="h-5 w-5 text-slate-400 mr-3 mt-0.5" />
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider">Date & Time</p>
            <p className="font-medium text-slate-900">{formattedDate} at {formattedTime}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AppointmentCard;
