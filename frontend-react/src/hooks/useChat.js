import { useState, useCallback, useEffect } from 'react';
import { chatService } from '../services/api';

export const useChat = (initialIntent) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingState, setLoadingState] = useState('');
  const [intent, setIntent] = useState(initialIntent);
  const [sessionId, setSessionId] = useState(null);

  const addMessage = useCallback((message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  // Start the session when the component mounts
  useEffect(() => {
    let mounted = true;

    const initSession = async () => {
      try {
        setIsLoading(true);
        const response = await chatService.startSession(intent);
        if (mounted) {
          setSessionId(response.session_id);
          addMessage({ role: 'assistant', content: response.message });
        }
      } catch (error) {
        console.error('Failed to start session:', error);
        if (mounted) {
          addMessage({ role: 'assistant', content: 'Could not connect to the server.', isError: true });
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    if (intent && !sessionId && messages.length === 0) {
      initSession();
    }

    return () => { mounted = false; };
  }, [intent, sessionId, messages.length, addMessage]);

  const simulateLoadingStates = () => {
    const states = ['Coordinator...', 'Safety Check...', 'Routing...', 'Processing...'];
    let currentIndex = 0;
    
    setLoadingState(states[currentIndex]);
    
    const interval = setInterval(() => {
      currentIndex++;
      if (currentIndex < states.length) {
        setLoadingState(states[currentIndex]);
      } else {
        clearInterval(interval);
      }
    }, 800);
    
    return interval;
  };

  const sendMessage = async (text) => {
    if (!sessionId) return; // Cannot send message without a session

    const userMessage = { role: 'user', content: text };
    addMessage(userMessage);
    
    setIsLoading(true);
    const interval = simulateLoadingStates();

    try {
      const response = await chatService.replySession(sessionId, text);
      
      const assistantMessage = {
        role: 'assistant',
        content: response.message,
        data: response // Store the full response data for cards (e.g. appointment data, safety status)
      };
      
      addMessage(assistantMessage);
    } catch (error) {
      console.error('Chat error:', error);
      addMessage({
        role: 'assistant',
        content: 'Sorry, I encountered an error communicating with the server.',
        isError: true
      });
    } finally {
      clearInterval(interval);
      setIsLoading(false);
      setLoadingState('');
    }
  };

  return {
    messages,
    isLoading,
    loadingState,
    sendMessage,
    addMessage,
    intent,
    setIntent
  };
};
