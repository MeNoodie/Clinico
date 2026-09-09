'use client'

import { FormEvent, useEffect, useState } from 'react'
import { api } from '@/lib/api'
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Database,
  Route,
  Siren,
  Bell,
  CalendarDays,
  Check,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  Clock3,
  FileText,
  Home,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Mail,
  Menu,
  MessageCircle,
  Paperclip,
  Phone,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Upload,
  User,
  UserRound,
  X,
} from 'lucide-react'

type View = 'home' | 'signup' | 'login' | 'dashboard' | 'appointments' | 'documents' | 'ai' | 'profile' | 'settings'

const appointments = [
  { date: '15', month: 'Aug 2026', doctor: 'Dr. Raj Sharma', specialty: 'Dentistry', time: '10:00 AM' },
  { date: '28', month: 'Aug 2026', doctor: 'Dr. Neha Gupta', specialty: 'Cardiology', time: '11:30 AM' },
  { date: '12', month: 'Sep 2026', doctor: 'Dr. Amit Verma', specialty: 'General Physician', time: '09:00 AM' },
]

const navItems: { view: View; label: string; icon: typeof Home }[] = [
  { view: 'dashboard', label: 'Dashboard', icon: Home },
  { view: 'appointments', label: 'Appointments', icon: CalendarDays },
  { view: 'documents', label: 'Documents', icon: FileText },
  { view: 'ai', label: 'Clinico AI', icon: MessageCircle },
  { view: 'profile', label: 'Profile', icon: UserRound },
  { view: 'settings', label: 'Settings', icon: Settings },
]

function Logo({ onClick }: { onClick?: () => void }) {
  return <button onClick={onClick} className="clinico-logo" aria-label="Go to Clinico home">Clinico</button>
}

function MedicalIllustration({ kind = 'doctor' }: { kind?: 'doctor' | 'patient' }) {
  return (
    <div className={`medical-illustration ${kind}`} aria-hidden="true">
      <div className="illustration-sun" />
      <div className="illustration-person">
        <div className="person-hair" />
        <div className="person-face" />
        <div className="person-body" />
        <div className="person-screen" />
      </div>
      <div className="illustration-cross"><Plus size={18} /></div>
      <div className="illustration-heart"><Activity size={18} /></div>
    </div>
  )
}

function Landing({ go }: { go: (view: View) => void }) {
  return (
    <div className="marketing-page">
      <header className="marketing-header page-width">
        <Logo onClick={() => go('home')} />
        <nav className="marketing-nav" aria-label="Primary navigation"><a className="active" href="#home">Home</a><a href="#features">Features</a><a href="#about">About</a></nav>
        <div className="header-actions"><button className="text-button" onClick={() => go('login')}>Login</button><button className="primary-button small" onClick={() => go('signup')}>Sign Up <ArrowRight size={14} /></button></div>
      </header>
      <main>
        <section id="home" className="hero page-width">
          <div className="hero-copy">
            <span className="eyebrow"><ShieldCheck size={13} /> Your Health, Our Priority</span>
            <h1>Smarter Healthcare<br /><em>Starts Here</em></h1>
            <p>Book appointments, manage your health records, and get AI-powered assistance — all in one secure place.</p>
            <div className="hero-actions"><button className="primary-button" onClick={() => go('signup')}>Get Started <ArrowRight size={16} /></button><button className="secondary-button" onClick={() => document.querySelector('#features')?.scrollIntoView({ behavior: 'smooth' })}>Explore Features <ArrowRight size={15} /></button></div>
            <div className="hero-proof"><span><ShieldCheck size={15} /> Secure by design</span><span><Activity size={15} /> AI-assisted care</span></div>
          </div>
          <div className="hero-visual"><MedicalIllustration kind="doctor" /><div className="floating-card card-one"><CalendarDays size={22} /><span><b>Book Appointments</b><small>Easily</small></span></div><div className="floating-card card-two"><FileText size={22} /><span><b>Upload & Access</b><small>Your Medical Documents</small></span></div><div className="floating-card card-three"><MessageCircle size={22} /><span><b>Get AI Health</b><small>Assistance</small></span></div></div>
        </section>
        <section className="feature-row page-width">
          <Feature icon={<CalendarDays />} title="Book Appointments" copy="Find and book with top doctors in minutes." tone="blue" />
          <Feature icon={<FileText />} title="Document Upload" copy="Store and access your medical reports securely." tone="green" />
          <Feature icon={<MessageCircle />} title="AI-Powered Support" copy="Get instant answers to health queries." tone="purple" />
        </section>
        <FeaturesSection />
        <AboutSection />
      </main>
    </div>
  )
}

const platformFeatures = [
  { icon: <CalendarDays />, title: 'AI Appointment Assistant', copy: 'Interact with an intelligent assistant to book, cancel, reschedule, or follow up on appointments.', tone: 'blue' },
  { icon: <ClipboardList />, title: 'Smart Appointment Management', copy: 'View and manage appointments through a simple guided conversational experience.', tone: 'green' },
  { icon: <BrainCircuit />, title: 'Multi-Agent Intelligence', copy: 'Specialized AI agents coordinate safety checks, routing, information collection, and appointment actions.', tone: 'purple' },
  { icon: <Siren />, title: 'Safety-First Assistance', copy: 'Potential emergency situations are prioritized for immediate escalation instead of medical diagnosis.', tone: 'blue' },
  { icon: <Route />, title: 'Intelligent Department Routing', copy: 'Patient concerns are routed to the appropriate hospital department.', tone: 'green' },
  { icon: <FileText />, title: 'Medical Document Management', copy: 'Upload and manage medical reports, prescriptions, ECG reports, and healthcare documents.', tone: 'purple' },
]

function FeaturesSection() {
  return <section id="features" className="marketing-section page-width"><div className="section-intro"><span className="eyebrow">POWERFUL FEATURES</span><h2>Healthcare Administration, Powered by AI</h2><p>Clinico combines intelligent AI agents with healthcare workflows to help patients manage appointments, medical documents, and healthcare interactions from one platform.</p></div><div className="feature-grid">{platformFeatures.map((feature) => <Feature key={feature.title} {...feature} />)}</div></section>
}

function AboutSection() {
  return <section id="about" className="about-section page-width"><div className="section-intro"><span className="eyebrow">ABOUT CLINICO</span><h2>Making Healthcare Administration Smarter</h2><p>Clinico is an AI-powered healthcare administration platform designed to simplify how patients interact with healthcare services.</p><p>From booking appointments to managing follow-ups and medical documents, Clinico uses intelligent workflows to reduce administrative complexity and provide faster patient support.</p></div><div className="problem-solution"><article className="about-panel problem"><span className="panel-label">PROBLEM</span><h3>Healthcare administration shouldn&apos;t be complicated.</h3><p>Patients often wait on calls for simple appointment changes, while healthcare staff spend valuable time managing repetitive administrative tasks.</p></article><article className="about-panel solution"><span className="panel-label">SOLUTION</span><h3>One Intelligent System. Multiple Specialized Agents.</h3><p>Instead of relying on a single AI model for every task, Clinico uses a multi-agent workflow where specialized agents handle different responsibilities.</p></article></div><div className="agent-grid">{[{ icon: <UserRound />, title: 'Coordinator Agent', copy: 'Understands patient requests and collects necessary information.' }, { icon: <ShieldCheck />, title: 'Safety Agent', copy: 'Checks for potential emergency situations and prioritizes appropriate escalation.' }, { icon: <Route />, title: 'Routing Agent', copy: 'Routes patient concerns to the appropriate hospital department.' }, { icon: <Activity />, title: 'Action Agents', copy: 'Handle appointment booking, cancellation, rescheduling, and follow-up workflows.' }].map((agent) => <article className="agent-card" key={agent.title}><div className="icon-box blue">{agent.icon}</div><h3>{agent.title}</h3><p>{agent.copy}</p></article>)}</div><div className="workflow"><div className="workflow-node">User</div><span>↓</span><div className="workflow-node">Coordinator Agent</div><span>↓</span><div className="workflow-node">Safety Agent</div><span>↓</span><div className="workflow-node">Routing Agent</div><span>↓</span><div className="workflow-node">Action Agents</div><span>↓</span><div className="workflow-node database"><Database size={16} /> Healthcare Database</div></div></section>
}

function Feature({ icon, title, copy, tone }: { icon: React.ReactNode; title: string; copy: string; tone: string }) {
  return <article className="feature-card"><div className={`icon-box ${tone}`}>{icon}</div><div><h3>{title}</h3><p>{copy}</p></div></article>
}

function AuthPage({ mode, go }: { mode: 'signup' | 'login'; go: (view: View) => void }) {
  const signup = mode === 'signup'
  return <div className="auth-page"><div className="auth-side"><Logo onClick={() => go('home')} /><div className="auth-side-copy"><h1>{signup ? 'Join Clinico for a Healthier Tomorrow' : 'Welcome Back'}</h1><p>{signup ? 'Create your account to book appointments, manage records and get AI-powered assistance.' : 'Log in to access your appointments, medical documents and AI assistant.'}</p></div><MedicalIllustration kind={signup ? 'patient' : 'doctor'} /><i>“{signup ? 'Better care. A healthier you.' : 'Your Health Journey Continues Here.'}”</i></div><div className="auth-panel"><div className="auth-form"><h2>{signup ? 'Create Your Account' : 'Login to Your Account'}</h2><p className="form-subtitle">{signup ? <>Already have an account? <button onClick={() => go('login')}>Login</button></> : <>Don&apos;t have an account? <button onClick={() => go('signup')}>Sign Up</button></>}</p><form onSubmit={(e) => { e.preventDefault(); go('dashboard') }}>
    {signup && <Field icon={<User />} label="Full Name" placeholder="Enter your full name" />}
    <Field icon={<Mail />} label="Email Address" placeholder="Enter your email" type="email" />
    {signup && <Field icon={<Phone />} label="Phone Number" placeholder="Enter your phone number" />}
    <Field icon={<LockKeyhole />} label="Password" placeholder={signup ? 'Create a password' : 'Enter your password'} type="password" />
    {!signup && <div className="forgot">Forgot Password?</div>}
    <button className="primary-button full" type="submit">{signup ? 'Sign Up' : 'Login'}</button>
  </form>{signup ? <p className="legal">By signing up, you agree to our <a>Terms of Service</a> and <a>Privacy Policy.</a></p> : <><div className="or-divider">or continue with</div><button className="social-button"><b className="google">G</b> Continue with Google</button><button className="social-button"><b className="microsoft">⊞</b> Continue with Microsoft</button></>}</div></div></div>
}

function Field({ icon, label, placeholder, type = 'text' }: { icon: React.ReactNode; label: string; placeholder: string; type?: string }) {
  return <label className="field"><span>{icon}<b>{label}</b></span><div><input type={type} placeholder={placeholder} required />{type === 'password' && <CircleHelp size={15} />}</div></label>
}

function AppShell({ view, go }: { view: View; go: (view: View) => void }) {
  const [menuOpen, setMenuOpen] = useState(false)
  return <div className="app-shell"><header className="app-header"><Logo onClick={() => go('dashboard')} /><button className="mobile-menu" onClick={() => setMenuOpen(!menuOpen)}><Menu /></button><div className="app-header-actions"><Bell size={18} /><div className="user-chip"><span>P</span><small><b>Piyush</b>Patient</small><ChevronDown size={14} /></div></div></header><div className="app-body"><aside className={menuOpen ? 'sidebar open' : 'sidebar'}>{navItems.map(({ view: itemView, label, icon: Icon }) => <button key={itemView} className={view === itemView ? 'nav-item active' : 'nav-item'} onClick={() => { go(itemView); setMenuOpen(false) }}><Icon size={17} />{label}</button>)}<button className="logout" onClick={() => go('home')}><LogOut size={17} />Logout</button></aside><main className="app-content">{view === 'dashboard' && <Dashboard go={go} />}{view === 'appointments' && <Appointments go={go} />}{view === 'documents' && <Documents />}{view === 'ai' && <ClinicoAI />}{view === 'profile' && <Profile />}{view === 'settings' && <SettingsPage />}</main></div></div>
}

function PageHeading({ title, copy, action }: { title: string; copy: string; action?: React.ReactNode }) { return <div className="page-heading"><div><h1>{title}</h1><p>{copy}</p></div>{action}</div> }
function Stat({ icon, title, value, tone }: { icon: React.ReactNode; title: string; value: string; tone: string }) { return <div className="stat-card"><div className={`icon-box ${tone}`}>{icon}</div><div><small>{title}</small><strong>{value}</strong></div></div> }
function Dashboard({ go }: { go: (view: View) => void }) { return <><PageHeading title="Welcome Back, Piyush!" copy="Here’s an overview of your health journey." /><div className="stats-grid"><Stat icon={<CalendarDays />} title="Upcoming Appointments" value="2" tone="blue" /><Stat icon={<FileText />} title="Total Documents" value="5" tone="green" /><Stat icon={<MessageCircle />} title="AI Conversations" value="12" tone="purple" /></div><h2 className="section-title">Quick Actions</h2><div className="quick-actions"><button onClick={() => go('appointments')}><span className="icon-box blue"><CalendarDays /></span><b>Book New Appointment</b><small>Find and schedule with a doctor</small></button><button onClick={() => go('documents')}><span className="icon-box green"><FileText /></span><b>Upload Document</b><small>Add your medical reports</small></button><button onClick={() => go('ai')}><span className="icon-box purple"><MessageCircle /></span><b>Chat with Clinico AI</b><small>Get instant health assistance</small></button></div><div className="section-title-row"><h2 className="section-title">Upcoming Appointment</h2><button className="link-button" onClick={() => go('appointments')}>View All</button></div><AppointmentCard appointment={appointments[0]} /></> }
function AppointmentCard({ appointment, compact = false }: { appointment: typeof appointments[number]; compact?: boolean }) { return <div className={compact ? 'appointment-card compact' : 'appointment-card'}><div className="date-tile"><strong>{appointment.date}</strong><small>{appointment.month}</small></div><div className="appointment-info"><b>{appointment.doctor}</b><span>{appointment.specialty}</span><small>{appointment.time}</small></div><div className="appointment-actions"><button>View Details</button><button>Reschedule</button><button className="danger">Cancel</button><button>Follow Up</button></div></div> }
function Appointments({ go }: { go: (view: View) => void }) { return <><PageHeading title="My Appointments" copy="Manage your appointments and follow-ups." action={<button className="primary-button"><Plus size={16} /> New Appointment</button>} /><div className="tabs"><button className="selected">Upcoming</button><button>Past</button><button>Cancelled</button></div><div className="appointment-list">{appointments.map((appointment) => <AppointmentCard key={appointment.date} appointment={appointment} compact />)}</div><button className="back-link" onClick={() => go('dashboard')}>Back to dashboard</button></> }
function Documents() { const [uploaded, setUploaded] = useState(false); return <><PageHeading title="Upload Medical Document" copy="Upload and manage your medical reports." /><div className="documents-layout"><div className="upload-zone"><Upload size={34} /><h3>{uploaded ? 'Document uploaded successfully' : 'Drag and drop your file here'}</h3><button onClick={() => setUploaded(true)}>or click to upload</button><small>Supported formats: PDF, JPG, JPEG, PNG (Max 10MB)</small></div><div className="category-panel"><h3>Document Categories</h3>{['ECG Reports', 'Blood Test Reports', 'Urine Test Reports', 'X-Ray Reports', 'Prescription'].map((name, index) => <div className="category" key={name}><span>{index === 0 ? <Activity /> : index === 4 ? <LockKeyhole /> : <ClipboardList />}</span>{name}</div>)}</div></div></> }
function ClinicoAI() { const [message, setMessage] = useState(''); const [sent, setSent] = useState(false); return <><PageHeading title="Clinico AI" copy="Ask anything about your health, appointments, or reports." /><div className="ai-layout"><div className="chat-panel"><div className="chat-message"><span className="ai-avatar">AI</span><div><b>Hello! I’m Clinico AI. How can I help you today?</b><p>You can ask me about:<br />• Book an appointment<br />• Check your appointments<br />• Understand your medical reports<br />• General health questions</p></div></div>{sent && <div className="chat-message user-message"><span className="ai-avatar">P</span><div>{message}</div></div>}<div className="chat-input"><input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Type your message here..." onKeyDown={(e) => { if (e.key === 'Enter' && message) { setSent(true); setMessage('') } }} /><Paperclip size={17} /><button onClick={() => { if (message) { setSent(true); setMessage('') } }}><Send size={16} /></button></div></div><div className="suggestions"><h3>Try these examples</h3>{['Book an appointment', 'Explain my blood test report', 'When is my next appointment?', 'What departments are available?', 'Help me reschedule my appointment'].map((text) => <button key={text} onClick={() => setMessage(text)}><Search size={14} />{text}</button>)}</div></div></> }
function Profile() { return <><PageHeading title="My Profile" copy="Manage your personal health information." /><div className="settings-card profile-card"><div className="profile-avatar">P</div><div className="profile-name"><h2>Piyush</h2><p>Patient</p></div><button className="secondary-button">Edit Profile</button><div className="profile-fields"><Field icon={<User />} label="Full Name" placeholder="Piyush" /><Field icon={<Mail />} label="Email Address" placeholder="piyush@example.com" /><Field icon={<Phone />} label="Phone Number" placeholder="+91 98765 43210" /></div></div></> }
function SettingsPage() { return <><PageHeading title="Settings" copy="Manage your account preferences and privacy." /><div className="settings-card"><SettingRow icon={<Bell />} title="Notifications" copy="Receive reminders for your appointments and updates." /><SettingRow icon={<LockKeyhole />} title="Privacy & Security" copy="Manage your password and account security." /><SettingRow icon={<CircleHelp />} title="Help & Support" copy="Get answers to common questions." /></div></> }
function SettingRow({ icon, title, copy }: { icon: React.ReactNode; title: string; copy: string }) { const [checked, setChecked] = useState(true); return <div className="setting-row"><span className="setting-icon">{icon}</span><div><b>{title}</b><p>{copy}</p></div><button className={checked ? 'toggle checked' : 'toggle'} onClick={() => setChecked(!checked)} aria-label={`Toggle ${title}`}><span /></button></div> }

type Auth = { access_token: string; user_id: number; patient_id: number }
type ProfileData = { user_id: number; patient_id: number; name: string; email: string; phone: string }
type AppointmentData = { appointment_id: number; datetime: string; status: string; doctor_name: string; department_name: string; can_cancel: boolean; can_reschedule: boolean; can_followup: boolean }

function ConnectedAuth({ mode, go, signedIn }: { mode: 'signup' | 'login'; go: (view: View) => void; signedIn: (auth: Auth, profile: ProfileData) => void }) {
  const signup = mode === 'signup', [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const values = new FormData(event.currentTarget); const payload = Object.fromEntries(values); try { const auth = await api<Auth>(signup ? '/auth/signup' : '/auth/login', undefined, { method: 'POST', body: JSON.stringify(payload) }); const profile = await api<ProfileData>('/auth/me', auth.access_token); signedIn(auth, profile); go('dashboard') } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to sign in') } }
  return <div className="auth-page"><div className="auth-side"><Logo onClick={() => go('home')} /><div className="auth-side-copy"><h1>{signup ? 'Join Clinico for a Healthier Tomorrow' : 'Welcome Back'}</h1><p>Manage appointments and get AI-powered assistance.</p></div></div><div className="auth-panel"><div className="auth-form"><h2>{signup ? 'Create Your Account' : 'Login to Your Account'}</h2><form onSubmit={submit}>{signup && <label className="field"><span><User size={14}/><b>Full Name</b></span><div><input name="name" required /></div></label>}<label className="field"><span><Mail size={14}/><b>Email Address</b></span><div><input name="email" type="email" required /></div></label>{signup && <label className="field"><span><Phone size={14}/><b>Phone Number</b></span><div><input name="phone" required /></div></label>}<label className="field"><span><LockKeyhole size={14}/><b>Password</b></span><div><input name="password" type="password" required /></div></label>{error && <p className="form-error">{error}</p>}<button className="primary-button full">{signup ? 'Sign Up' : 'Login'}</button></form><p className="form-subtitle">{signup ? <>Already have an account? <button onClick={() => go('login')}>Login</button></> : <>Don&apos;t have an account? <button onClick={() => go('signup')}>Sign Up</button></>}</p></div></div></div>
}

function ConnectedApp({ view, go, auth, profile, logout }: { view: View; go: (view: View) => void; auth: Auth; profile: ProfileData; logout: () => void }) {
  const [appointments, setAppointments] = useState<AppointmentData[]>([]), [chat, setChat] = useState<string[]>(['Hello! I’m Clinico AI. How can I help you today?']), [message, setMessage] = useState(''), [sessionId, setSessionId] = useState(''), [error, setError] = useState('')
  const loadAppointments = () => api<{history: AppointmentData[]}>('/appointments/history', auth.access_token).then((data) => setAppointments(data.history)).catch((cause) => setError(cause.message))
  useEffect(() => { if (view === 'appointments' || view === 'dashboard') loadAppointments() }, [view])
  async function action(appointment: AppointmentData, kind: 'cancel' | 'reschedule' | 'followup') { try { const result = await api<{session_id: string; message: string}>(`/appointments/${appointment.appointment_id}/${kind}`, auth.access_token, { method: 'POST' }); setSessionId(result.session_id); setChat([result.message]); go('ai') } catch (cause) { setError(cause instanceof Error ? cause.message : 'Action failed') } }
  async function send() { if (!message.trim()) return; const text = message; setMessage(''); setChat((current) => [...current, `You: ${text}`]); try { let id = sessionId; if (!id) { const opened = await api<{session_id: string; message: string}>('/chat/session/start', auth.access_token, { method: 'POST', body: '{}' }); id = opened.session_id; setSessionId(id); setChat((current) => [...current, opened.message]) } const reply = await api<{message: string; done: boolean}>('/chat/session/reply', auth.access_token, { method: 'POST', body: JSON.stringify({ session_id: id, message: text }) }); setChat((current) => [...current, reply.message]); if (reply.done) setSessionId('') } catch (cause) { setError(cause instanceof Error ? cause.message : 'Chat failed') } }
  const card = (appointment: AppointmentData) => { const date = new Date(appointment.datetime); return <div className="appointment-card" key={appointment.appointment_id}><div className="date-tile"><strong>{date.getDate()}</strong><small>{date.toLocaleDateString(undefined, {month:'short', year:'numeric'})}</small></div><div className="appointment-info"><b>{appointment.doctor_name}</b><span>{appointment.department_name}</span><small>{date.toLocaleString()} · {appointment.status}</small></div><div className="appointment-actions">{appointment.can_reschedule && <button onClick={() => action(appointment, 'reschedule')}>Reschedule</button>}{appointment.can_cancel && <button className="danger" onClick={() => action(appointment, 'cancel')}>Cancel</button>}{appointment.can_followup && <button onClick={() => action(appointment, 'followup')}>Follow Up</button>}</div></div> }
  return <div className="app-shell"><header className="app-header"><Logo onClick={() => go('dashboard')} /><div className="user-chip"><span>{profile.name[0]}</span><small><b>{profile.name}</b>Patient</small></div></header><div className="app-body"><aside className="sidebar">{navItems.filter((item) => item.view !== 'settings').map(({view: itemView, label, icon: Icon}) => <button key={itemView} className={view === itemView ? 'nav-item active' : 'nav-item'} onClick={() => go(itemView)}><Icon size={17}/>{label}</button>)}<button className="logout" onClick={logout}><LogOut size={17}/>Logout</button></aside><main className="app-content">{error && <p className="form-error">{error}</p>}{view === 'dashboard' && <><PageHeading title={`Welcome Back, ${profile.name}!`} copy="Here’s an overview of your health journey."/><div className="quick-actions"><button onClick={() => go('appointments')}>Manage appointments</button><button onClick={() => go('ai')}>Chat with Clinico AI</button></div><h2 className="section-title">Upcoming Appointment</h2>{appointments[0] ? card(appointments[0]) : <p>No appointments found.</p>}</>}{view === 'appointments' && <><PageHeading title="My Appointments" copy="Manage your appointments and follow-ups." action={<button className="primary-button" onClick={() => { setSessionId(''); setChat(['Tell me your concern and preferred date/time.']); go('ai') }}><Plus size={16}/> New Appointment</button>}/><div className="appointment-list">{appointments.map(card)}</div></>}{view === 'ai' && <><PageHeading title="Clinico AI" copy="Ask about appointments or book a visit."/><div className="ai-layout"><div className="chat-panel"><div>{chat.map((item, index) => <div className="chat-message" key={index}><span className="ai-avatar">{item.startsWith('You:') ? 'P' : 'AI'}</span><div>{item}</div></div>)}</div><div className="chat-input"><input value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && send()} placeholder="Type your message here..."/><button onClick={send}><Send size={16}/></button></div></div></div></>}{view === 'profile' && <><PageHeading title="My Profile" copy="Your account details."/><div className="settings-card profile-card"><div className="profile-avatar">{profile.name[0]}</div><div className="profile-name"><h2>{profile.name}</h2><p>{profile.email}<br/>{profile.phone}</p></div></div></>}{view === 'documents' && <PageHeading title="Documents" copy="Document upload is not yet available in the backend."/>}</main></div></div>
}

export default function ClinicoApp() { const [view, setView] = useState<View>('home'), [auth, setAuth] = useState<Auth | null>(null), [profile, setProfile] = useState<ProfileData | null>(null); useEffect(() => { const raw = localStorage.getItem('clinico-auth'); if (!raw) return; const saved = JSON.parse(raw) as Auth; api<ProfileData>('/auth/me', saved.access_token).then((me) => { setAuth(saved); setProfile(me); setView('dashboard') }).catch(() => localStorage.removeItem('clinico-auth')) }, []); const signedIn = (newAuth: Auth, me: ProfileData) => { localStorage.setItem('clinico-auth', JSON.stringify(newAuth)); setAuth(newAuth); setProfile(me) }; const logout = () => { localStorage.removeItem('clinico-auth'); setAuth(null); setProfile(null); setView('home') }; if (view === 'home') return <Landing go={setView}/>; if (view === 'signup' || view === 'login') return <ConnectedAuth mode={view} go={setView} signedIn={signedIn}/>; return auth && profile ? <ConnectedApp view={view} go={setView} auth={auth} profile={profile} logout={logout}/> : <Landing go={setView}/> }
