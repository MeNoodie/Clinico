import React, { useEffect, useState } from 'react';
import { Calendar } from 'lucide-react';
import api from '../services/api';
import AppointmentCard from '../components/AppointmentCard';

const History = () => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await api.get('/appointments/history');
        setAppointments(response.data.history || []);
      } catch (error) {
        console.error("Failed to fetch history", error);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const upcoming = appointments.filter(a => new Date(a.datetime) > new Date() && a.status !== 'CANCELLED');
  const past = appointments.filter(a => new Date(a.datetime) <= new Date() || a.status === 'CANCELLED');

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Appointment History</h1>
      
      {loading ? (
        <div className="text-center text-slate-500 py-10">Loading appointments...</div>
      ) : (
        <div className="space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center">
              <Calendar className="mr-2 h-5 w-5 text-primary-500" />
              Upcoming Appointments
            </h2>
            {upcoming.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 text-center text-slate-500">
                No upcoming appointments found.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {upcoming.map(appt => (
                  <AppointmentCard key={appt.appointment_id} appointment={{
                    appointment_id: appt.appointment_id,
                    booked_datetime: appt.datetime,
                    department: appt.department_name,
                    doctor: appt.doctor_name
                  }} />
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center">
              <Calendar className="mr-2 h-5 w-5 text-slate-400" />
              Past & Cancelled Appointments
            </h2>
            {past.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 text-center text-slate-500">
                No past appointments found.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {past.map(appt => (
                  <AppointmentCard key={appt.appointment_id} appointment={{
                    appointment_id: appt.appointment_id,
                    booked_datetime: appt.datetime,
                    department: appt.department_name,
                    doctor: appt.doctor_name
                  }} />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
};

export default History;
