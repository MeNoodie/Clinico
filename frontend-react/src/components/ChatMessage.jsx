import React from 'react';
import AppointmentCard from './AppointmentCard';
import EmergencyAlert from './EmergencyAlert';
import { Bot, User } from 'lucide-react';

const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user';
  const isEmergency = message.data?.safety_status === 'EMERGENCY';
  const hasAppointment = message.data?.appointment_id;

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} my-6`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        
        {/* Avatar */}
        <div className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center ${
          isUser ? 'bg-primary-600 ml-4' : 'bg-white border border-slate-200 mr-4'
        }`}>
          {isUser ? (
            <User className="h-5 w-5 text-white" />
          ) : (
            <Bot className="h-6 w-6 text-primary-600" />
          )}
        </div>

        {/* Message Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div className={`px-5 py-3.5 rounded-2xl ${
            isUser 
              ? 'bg-primary-600 text-white rounded-tr-sm' 
              : message.isError 
                ? 'bg-red-50 text-red-900 border border-red-100 rounded-tl-sm'
                : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm'
          }`}>
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          </div>

          {/* Conditional Cards based on backend response data */}
          {!isUser && isEmergency && (
            <EmergencyAlert message={message.data?.message} />
          )}

          {!isUser && hasAppointment && (
            <AppointmentCard appointment={message.data} />
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
