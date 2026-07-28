import React, { useEffect, useRef } from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import ChatMessage from '../components/ChatMessage';
import MessageInput from '../components/MessageInput';
import LoadingTimeline from '../components/LoadingTimeline';
import { Bot } from 'lucide-react';

const Chat = () => {
  const location = useLocation();
  const intent = location.state?.intent;
  
  const { 
    messages, 
    isLoading, 
    loadingState, 
    sendMessage, 
    addMessage 
  } = useChat(intent);
  
  const messagesEndRef = useRef(null);



  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loadingState]);

  // Redirect to dashboard if no intent is provided
  if (!intent) {
    return <Navigate to="/dashboard" replace />;
  }

  const getWorkflowTitle = () => {
    switch(intent) {
      case 'BOOK_APPOINTMENT': return 'Booking Appointment';
      case 'RESCHEDULE_APPOINTMENT': return 'Rescheduling Appointment';
      case 'CANCEL_APPOINTMENT': return 'Canceling Appointment';
      case 'FOLLOWUP_APPOINTMENT': return 'Follow-up Appointment';
      default: return 'AgentCare Assistant';
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 py-4 px-6 flex items-center shadow-sm z-10">
        <div className="bg-primary-100 p-2 rounded-lg mr-3">
          <Bot className="h-6 w-6 text-primary-600" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900">{getWorkflowTitle()}</h2>
          <p className="text-sm text-slate-500 flex items-center">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2"></span>
            Agent Online
          </p>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-grow overflow-y-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-4xl mx-auto flex flex-col">
          {messages.map((msg, index) => (
            <ChatMessage key={index} message={msg} />
          ))}
          
          {isLoading && (
            <div className="flex w-full justify-start my-4">
              <div className="flex max-w-[80%] flex-row items-center">
                <div className="flex-shrink-0 h-10 w-10 rounded-full bg-white border border-slate-200 mr-4 flex items-center justify-center">
                  <Bot className="h-6 w-6 text-primary-600" />
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm shadow-sm">
                  <LoadingTimeline status={loadingState} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <MessageInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
};

export default Chat;
