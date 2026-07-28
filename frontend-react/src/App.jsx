import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Upload, Bot, CheckCircle, AlertCircle, LayoutDashboard, MessageSquare, LogOut, User as UserIcon } from 'lucide-react';
import './App.css';

const API_URL = 'http://127.0.0.1:8000';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [patientId, setPatientId] = useState(localStorage.getItem('patientId') || '');
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'dashboard'

  // Auth form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [authError, setAuthError] = useState('');

  useEffect(() => {
    if (token && patientId) {
      setIsAuthenticated(true);
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, [token, patientId]);

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      let res;
      if (authMode === 'login') {
        res = await axios.post(`${API_URL}/auth/login`, { email, password });
      } else {
        res = await axios.post(`${API_URL}/auth/signup`, { name, email, phone, password });
      }
      
      const { access_token, patient_id } = res.data;
      setToken(access_token);
      setPatientId(patient_id);
      localStorage.setItem('token', access_token);
      localStorage.setItem('patientId', patient_id);
      setIsAuthenticated(true);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (err) {
      setAuthError(err.response?.data?.detail || 'Authentication failed');
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setToken('');
    setPatientId('');
    localStorage.removeItem('token');
    localStorage.removeItem('patientId');
    delete axios.defaults.headers.common['Authorization'];
  };

  if (!isAuthenticated) {
    return (
      <div className="app-container auth-bg">
        <div className="auth-card">
          <div className="auth-header">
            <Bot size={40} className="header-icon" />
            <h2>AgentCare Clinico</h2>
            <p>{authMode === 'login' ? 'Welcome back' : 'Create your patient account'}</p>
          </div>
          <form onSubmit={handleAuth} className="auth-form">
            {authMode === 'signup' && (
              <>
                <input type="text" placeholder="Full Name" value={name} onChange={e => setName(e.target.value)} required />
                <input type="text" placeholder="Phone Number" value={phone} onChange={e => setPhone(e.target.value)} required />
              </>
            )}
            <input type="email" placeholder="Email Address" value={email} onChange={e => setEmail(e.target.value)} required />
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
            
            {authError && <div className="auth-error">{authError}</div>}
            
            <button type="submit" className="auth-btn">
              {authMode === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
          </form>
          <div className="auth-switch">
            {authMode === 'login' ? (
              <p>Don't have an account? <span onClick={() => setAuthMode('signup')}>Sign up</span></p>
            ) : (
              <p>Already have an account? <span onClick={() => setAuthMode('login')}>Sign in</span></p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Bot size={24} className="header-icon" />
          <h2>Clinico</h2>
        </div>
        <nav className="sidebar-nav">
          <button className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
            <MessageSquare size={18} /> Chat
          </button>
          <button className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={18} /> Dashboard
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="patient-info">
            <UserIcon size={16} /> Patient ID: {patientId}
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </aside>
      
      <main className="main-content">
        {activeTab === 'chat' ? <ChatInterface patientId={patientId} /> : <Dashboard />}
      </main>
    </div>
  );
}

function ChatInterface({ patientId }) {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! I'm AgentCare, your AI medical receptionist. How can I help you today?", sender: 'bot' }
  ]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    setSessionId(Math.random().toString(36).substring(7));
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { id: Date.now(), text: input, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/chat/test`, {
        patient_id: Number(patientId),
        message: input,
        session_id: sessionId
      });

      const botText = response.data.message;
      let debugInfo = `Intent: ${response.data.intent} | Safety: ${response.data.safety_status}`;
      if (response.data.department) debugInfo += ` | Dept: ${response.data.department}`;

      const botMessage = { 
        id: Date.now() + 1, 
        text: botText, 
        sender: 'bot',
        debug: debugInfo
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [...prev, { id: Date.now() + 1, text: 'Error communicating with server.', sender: 'bot', isError: true }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('patient_id', patientId);
    formData.append('file', file);

    setUploadStatus('uploading');
    try {
      const res = await axios.post(`${API_URL}/chat/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadStatus('success');
      setMessages((prev) => [...prev, { id: Date.now(), text: `Uploaded document: ${res.data.filename}`, sender: 'system' }]);
    } catch (error) {
      console.error(error);
      setUploadStatus('error');
    }
    setTimeout(() => setUploadStatus(null), 3000);
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div>
          <h2 style={{margin:0, fontSize: '1.2rem'}}>AgentCare Chat</h2>
        </div>
        <div className="header-controls">
          <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>
            <Upload size={18} /> Upload Document
          </button>
          <input type="file" ref={fileInputRef} onChange={handleFileUpload} style={{display: 'none'}} />
          {uploadStatus === 'uploading' && <span className="upload-indicator">...</span>}
          {uploadStatus === 'success' && <CheckCircle size={18} color="green" />}
          {uploadStatus === 'error' && <AlertCircle size={18} color="red" />}
        </div>
      </header>

      <div className="messages-list">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
            <div className="message-bubble">
              <p>{msg.text}</p>
              {msg.debug && <span className="debug-badge">{msg.debug}</span>}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper bot">
            <div className="message-bubble loading">
              <div className="dot-typing"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSend}>
        <input 
          type="text" 
          placeholder="Describe your symptoms or booking request..." 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          <Send size={20} />
        </button>
      </form>
    </div>
  );
}

function Dashboard() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_URL}/appointments/history`)
      .then(res => {
        setHistory(res.data.history);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div style={{padding: '2rem'}}>Loading dashboard...</div>;

  return (
    <div className="dashboard-container">
      <h2>Your Appointments</h2>
      {history.length === 0 ? (
        <p>No appointments found.</p>
      ) : (
        <div className="history-grid">
          {history.map(appt => (
            <div key={appt.appointment_id} className="history-card">
              <div className="appt-header">
                <span className={`status-badge ${appt.status.toLowerCase()}`}>{appt.status}</span>
                <span className="appt-id">ID: {appt.appointment_id}</span>
              </div>
              <div className="appt-body">
                <h3>{new Date(appt.datetime).toLocaleString()}</h3>
                <p><strong>Doctor:</strong> {appt.doctor_name}</p>
                <p><strong>Department:</strong> {appt.department_name}</p>
                <p className="appt-problem"><strong>Reason:</strong> {appt.problem}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
