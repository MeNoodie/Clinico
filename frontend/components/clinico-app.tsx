'use client'

import { FormEvent, useEffect, useRef, useState } from 'react'
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
  Loader2,
  Bot,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'


// ─── Types ────────────────────────────────────────────────────────────────────

type View = 'home' | 'signup' | 'login' | 'dashboard' | 'appointments' | 'documents' | 'ai' | 'profile' | 'settings'
type Auth = { access_token: string; user_id: number; patient_id: number }
type ProfileData = { user_id: number; patient_id: number; name: string; email: string; phone: string }
type AppointmentData = {
  appointment_id: number
  datetime: string
  status: string
  doctor_name: string
  department_name: string
  can_cancel: boolean
  can_reschedule: boolean
  can_followup: boolean
}

// role: 'ai' | 'user' | 'system'
type ChatMessage = {
  id: string
  role: 'ai' | 'user' | 'system'
  text: string
  timestamp: Date
}

// ─── Static data ──────────────────────────────────────────────────────────────

const staticAppointments = [
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

// ─── Helpers ──────────────────────────────────────────────────────────────────

function mkMsg(role: ChatMessage['role'], text: string): ChatMessage {
  return { id: crypto.randomUUID(), role, text, timestamp: new Date() }
}

/** Render backend text with newlines and basic bold/bullet support */
function RichText({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <span className="rich-text">
      {lines.map((line, i) => {
        const trimmed = line.trimStart()
        const isBullet = trimmed.startsWith('•') || trimmed.startsWith('-') || trimmed.startsWith('*')
        const isNumbered = /^\d+\./.test(trimmed)

        // Bold: **text**
        const parts = line.split(/(\*\*[^*]+\*\*)/)
        const rendered = parts.map((part, j) =>
          part.startsWith('**') && part.endsWith('**')
            ? <strong key={j}>{part.slice(2, -2)}</strong>
            : <span key={j}>{part}</span>
        )

        return (
          <span key={i} className={`rt-line${isBullet || isNumbered ? ' rt-bullet' : ''}`}>
            {rendered}
            {i < lines.length - 1 && <br />}
          </span>
        )
      })}
    </span>
  )
}

// ─── Shared UI atoms ──────────────────────────────────────────────────────────

function Logo({ onClick }: { onClick?: () => void }) {
  return (
    <button onClick={onClick} className="clinico-logo" aria-label="Go to Clinico home">
      Clinico
    </button>
  )
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

function Feature({ icon, title, copy, tone }: { icon: React.ReactNode; title: string; copy: string; tone: string }) {
  return (
    <article className="feature-card">
      <div className={`icon-box ${tone}`}>{icon}</div>
      <div><h3>{title}</h3><p>{copy}</p></div>
    </article>
  )
}

function PageHeading({ title, copy, action }: { title: string; copy: string; action?: React.ReactNode }) {
  return (
    <div className="page-heading">
      <div><h1>{title}</h1><p>{copy}</p></div>
      {action}
    </div>
  )
}

function Stat({ icon, title, value, tone }: { icon: React.ReactNode; title: string; value: string; tone: string }) {
  return (
    <div className="stat-card">
      <div className={`icon-box ${tone}`}>{icon}</div>
      <div><small>{title}</small><strong>{value}</strong></div>
    </div>
  )
}

function Field({ icon, label, placeholder, type = 'text' }: { icon: React.ReactNode; label: string; placeholder: string; type?: string }) {
  return (
    <label className="field">
      <span>{icon}<b>{label}</b></span>
      <div><input type={type} placeholder={placeholder} required />{type === 'password' && <CircleHelp size={15} />}</div>
    </label>
  )
}

function SettingRow({ icon, title, copy }: { icon: React.ReactNode; title: string; copy: string }) {
  const [checked, setChecked] = useState(true)
  return (
    <div className="setting-row">
      <span className="setting-icon">{icon}</span>
      <div><b>{title}</b><p>{copy}</p></div>
      <button className={checked ? 'toggle checked' : 'toggle'} onClick={() => setChecked(!checked)} aria-label={`Toggle ${title}`}><span /></button>
    </div>
  )
}

// ─── Chat message bubble ───────────────────────────────────────────────────────

function ChatBubble({ msg, userInitial }: { msg: ChatMessage; userInitial: string }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'

  if (isSystem) {
    return (
      <div className="chat-system-msg">
        <AlertCircle size={12} />
        <span>{msg.text}</span>
      </div>
    )
  }

  return (
    <div className={`chat-bubble-row ${isUser ? 'user' : 'ai'}`}>
      {!isUser && (
        <div className="bubble-avatar ai-avatar" aria-label="Clinico AI">
          <Bot size={12} />
        </div>
      )}
      <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-ai'}`}>
        {!isUser && <span className="bubble-sender">Clinico AI</span>}
        <RichText text={msg.text} />
        <span className="bubble-time">
          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      {isUser && (
        <div className="bubble-avatar user-avatar" aria-label="You">
          {userInitial}
        </div>
      )}
    </div>
  )
}

// ─── Agent Pipeline Trace ─────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { id: 'query', label: 'User Query', sub: 'Message received', icon: MessageCircle, color: '#2e7de9' },
  { id: 'coord', label: 'Coordinator Agent', sub: 'Analyzing intent…', icon: BrainCircuit, color: '#7c5ceb' },
  { id: 'safety', label: 'Safety Check', sub: 'Validating request…', icon: ShieldCheck, color: '#13a56f' },
  { id: 'router', label: 'Routing Agent', sub: 'Finding department…', icon: Route, color: '#e88c2e' },
  { id: 'action', label: 'Action Agent', sub: 'Processing request…', icon: Activity, color: '#d4466e' },
  { id: 'response', label: 'Response Agent', sub: 'Preparing your answer…', icon: Sparkles, color: '#2e7de9' },
] as const

function AgentPipelineTrace() {
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep(prev => Math.min(prev + 1, PIPELINE_STEPS.length - 1))
    }, 1400)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="pipeline-trace">
      <div className="pipeline-header">
        <Loader2 size={12} className="spin" />
        <span>Processing through AI agents…</span>
      </div>
      <div className="pipeline-steps">
        {PIPELINE_STEPS.map((step, i) => {
          const Icon = step.icon
          const isDone = i < activeStep
          const isActive = i === activeStep
          const isPending = i > activeStep
          return (
            <div key={step.id} className="pipeline-step-col">
              <div className={`pipeline-node ${isDone ? 'node-done' : isActive ? 'node-active' : 'node-pending'
                }`} style={isActive || isDone ? { '--node-color': step.color } as React.CSSProperties : {}}>
                <div className="pipeline-icon">
                  {isDone
                    ? <Check size={11} />
                    : isActive
                      ? <Icon size={13} />
                      : <Icon size={13} />}
                </div>
                <div className="pipeline-label">
                  <span className="pipeline-name">{step.label}</span>
                  {(isActive) && <span className="pipeline-sub">{step.sub}</span>}
                  {isDone && <span className="pipeline-sub done-sub">✓ Done</span>}
                </div>
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <div className={`pipeline-connector ${isDone ? 'connector-done' : isActive ? 'connector-active' : 'connector-pending'
                  }`} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Landing page ─────────────────────────────────────────────────────────────

const platformFeatures = [
  { icon: <CalendarDays />, title: 'AI Appointment Assistant', copy: 'Interact with an intelligent assistant to book, cancel, reschedule, or follow up on appointments.', tone: 'blue' },
  { icon: <ClipboardList />, title: 'Smart Appointment Management', copy: 'View and manage appointments through a simple guided conversational experience.', tone: 'green' },
  { icon: <BrainCircuit />, title: 'Multi-Agent Intelligence', copy: 'Specialized AI agents coordinate safety checks, routing, information collection, and appointment actions.', tone: 'purple' },
  { icon: <Siren />, title: 'Safety-First Assistance', copy: 'Potential emergency situations are prioritized for immediate escalation instead of medical diagnosis.', tone: 'blue' },
  { icon: <Route />, title: 'Intelligent Department Routing', copy: 'Patient concerns are routed to the appropriate hospital department.', tone: 'green' },
  { icon: <FileText />, title: 'Medical Document Management', copy: 'Upload and manage medical reports, prescriptions, ECG reports, and healthcare documents.', tone: 'purple' },
]

function FeaturesSection() {
  return (
    <section id="features" className="marketing-section page-width">
      <div className="section-intro">
        <span className="eyebrow">POWERFUL FEATURES</span>
        <h2>Healthcare Administration, Powered by AI</h2>
        <p>Clinico combines intelligent AI agents with healthcare workflows to help patients manage appointments, medical documents, and healthcare interactions from one platform.</p>
      </div>
      <div className="feature-grid">{platformFeatures.map((f) => <Feature key={f.title} {...f} />)}</div>
    </section>
  )
}

function AboutSection() {
  return (
    <section id="about" className="about-section page-width">
      <div className="section-intro">
        <span className="eyebrow">ABOUT CLINICO</span>
        <h2>Making Healthcare Administration Smarter</h2>
        <p>Clinico is an AI-powered healthcare administration platform designed to simplify how patients interact with healthcare services.</p>
        <p>From booking appointments to managing follow-ups and medical documents, Clinico uses intelligent workflows to reduce administrative complexity and provide faster patient support.</p>
      </div>
      <div className="problem-solution">
        <article className="about-panel problem">
          <span className="panel-label">PROBLEM</span>
          <h3>Healthcare administration shouldn&apos;t be complicated.</h3>
          <p>Patients often wait on calls for simple appointment changes, while healthcare staff spend valuable time managing repetitive administrative tasks.</p>
        </article>
        <article className="about-panel solution">
          <span className="panel-label">SOLUTION</span>
          <h3>One Intelligent System. Multiple Specialized Agents.</h3>
          <p>Instead of relying on a single AI model for every task, Clinico uses a multi-agent workflow where specialized agents handle different responsibilities.</p>
        </article>
      </div>
      <div className="agent-grid">
        {[
          { icon: <UserRound />, title: 'Coordinator Agent', copy: 'Understands patient requests and collects necessary information.' },
          { icon: <ShieldCheck />, title: 'Safety Agent', copy: 'Checks for potential emergency situations and prioritizes appropriate escalation.' },
          { icon: <Route />, title: 'Routing Agent', copy: 'Routes patient concerns to the appropriate hospital department.' },
          { icon: <Activity />, title: 'Action Agents', copy: 'Handle appointment booking, cancellation, rescheduling, and follow-up workflows.' },
        ].map((agent) => (
          <article className="agent-card" key={agent.title}>
            <div className="icon-box blue">{agent.icon}</div>
            <h3>{agent.title}</h3>
            <p>{agent.copy}</p>
          </article>
        ))}
      </div>
      <div className="workflow">
        <div className="workflow-node">User</div>
        <span>↓</span>
        <div className="workflow-node">Coordinator Agent</div>
        <span>↓</span>
        <div className="workflow-node">Safety Agent</div>
        <span>↓</span>
        <div className="workflow-node">Routing Agent</div>
        <span>↓</span>
        <div className="workflow-node">Action Agents</div>
        <span>↓</span>
        <div className="workflow-node database"><Database size={16} /> Healthcare Database</div>
      </div>
    </section>
  )
}

function Landing({ go }: { go: (view: View) => void }) {
  return (
    <div className="marketing-page">
      <header className="marketing-header page-width">
        <Logo onClick={() => go('home')} />
        <nav className="marketing-nav" aria-label="Primary navigation">
          <a className="active" href="#home">Home</a>
          <a href="#features">Features</a>
          <a href="#about">About</a>
        </nav>
        <div className="header-actions">
          <button className="text-button" onClick={() => go('login')}>Login</button>
          <button className="primary-button small" onClick={() => go('signup')}>Sign Up <ArrowRight size={14} /></button>
        </div>
      </header>
      <main>
        <section id="home" className="hero page-width">
          <div className="hero-copy">
            <span className="eyebrow"><ShieldCheck size={13} /> Your Health, Our Priority</span>
            <h1>Smarter Healthcare<br /><em>Starts Here</em></h1>
            <p>Book appointments, manage your health records, and get AI-powered assistance — all in one secure place.</p>
            <div className="hero-actions">
              <button className="primary-button" onClick={() => go('signup')}>Get Started <ArrowRight size={16} /></button>
              <button className="secondary-button" onClick={() => document.querySelector('#features')?.scrollIntoView({ behavior: 'smooth' })}>Explore Features <ArrowRight size={15} /></button>
            </div>
            <div className="hero-proof">
              <span><ShieldCheck size={15} /> Secure by design</span>
              <span><Activity size={15} /> AI-assisted care</span>
            </div>
          </div>
          <div className="hero-visual">
            <MedicalIllustration kind="doctor" />
            <div className="floating-card card-one"><CalendarDays size={22} /><span><b>Book Appointments</b><small>Easily</small></span></div>
            <div className="floating-card card-two"><FileText size={22} /><span><b>Upload &amp; Access</b><small>Your Medical Documents</small></span></div>
            <div className="floating-card card-three"><MessageCircle size={22} /><span><b>Get AI Health</b><small>Assistance</small></span></div>
          </div>
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

// ─── Auth ─────────────────────────────────────────────────────────────────────

function AuthPage({ mode, go }: { mode: 'signup' | 'login'; go: (view: View) => void }) {
  const signup = mode === 'signup'
  return (
    <div className="auth-page">
      <div className="auth-side">
        <Logo onClick={() => go('home')} />
        <div className="auth-side-copy">
          <h1>{signup ? 'Join Clinico for a Healthier Tomorrow' : 'Welcome Back'}</h1>
          <p>{signup ? 'Create your account to book appointments, manage records and get AI-powered assistance.' : 'Log in to access your appointments, medical documents and AI assistant.'}</p>
        </div>
        <MedicalIllustration kind={signup ? 'patient' : 'doctor'} />
        <i>&quot;{signup ? 'Better care. A healthier you.' : 'Your Health Journey Continues Here.'}&quot;</i>
      </div>
      <div className="auth-panel">
        <div className="auth-form">
          <h2>{signup ? 'Create Your Account' : 'Login to Your Account'}</h2>
          <p className="form-subtitle">{signup ? <><span>Already have an account? </span><button onClick={() => go('login')}>Login</button></> : <><span>Don&apos;t have an account? </span><button onClick={() => go('signup')}>Sign Up</button></>}</p>
          <form onSubmit={(e) => { e.preventDefault(); go('dashboard') }}>
            {signup && <Field icon={<User />} label="Full Name" placeholder="Enter your full name" />}
            <Field icon={<Mail />} label="Email Address" placeholder="Enter your email" type="email" />
            {signup && <Field icon={<Phone />} label="Phone Number" placeholder="Enter your phone number" />}
            <Field icon={<LockKeyhole />} label="Password" placeholder={signup ? 'Create a password' : 'Enter your password'} type="password" />
            {!signup && <div className="forgot">Forgot Password?</div>}
            <button className="primary-button full" type="submit">{signup ? 'Sign Up' : 'Login'}</button>
          </form>
          {signup
            ? <p className="legal">By signing up, you agree to our <a href="#">Terms of Service</a> and <a href="#">Privacy Policy.</a></p>
            : <><div className="or-divider">or continue with</div><button className="social-button"><b className="google">G</b> Continue with Google</button><button className="social-button"><b className="microsoft">⊞</b> Continue with Microsoft</button></>
          }
        </div>
      </div>
    </div>
  )
}

function ConnectedAuth({ mode, go, signedIn }: { mode: 'signup' | 'login'; go: (view: View) => void; signedIn: (auth: Auth, profile: ProfileData) => void }) {
  const signup = mode === 'signup'
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)
    const values = new FormData(event.currentTarget)
    const payload = Object.fromEntries(values)
    try {
      const auth = await api<Auth>(signup ? '/auth/signup' : '/auth/login', undefined, { method: 'POST', body: JSON.stringify(payload) })
      const profile = await api<ProfileData>('/auth/me', auth.access_token)
      signedIn(auth, profile)
      go('dashboard')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to sign in')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-side">
        <Logo onClick={() => go('home')} />
        <div className="auth-side-copy">
          <h1>{signup ? 'Join Clinico for a Healthier Tomorrow' : 'Welcome Back'}</h1>
          <p>Manage appointments and get AI-powered assistance.</p>
        </div>
        <MedicalIllustration kind={signup ? 'patient' : 'doctor'} />
      </div>
      <div className="auth-panel">
        <div className="auth-form">
          <h2>{signup ? 'Create Your Account' : 'Login to Your Account'}</h2>
          <form onSubmit={submit}>
            {signup && (
              <label className="field">
                <span><User size={14} /><b>Full Name</b></span>
                <div><input name="name" required /></div>
              </label>
            )}
            <label className="field">
              <span><Mail size={14} /><b>Email Address</b></span>
              <div><input name="email" type="email" required /></div>
            </label>
            {signup && (
              <label className="field">
                <span><Phone size={14} /><b>Phone Number</b></span>
                <div><input name="phone" required /></div>
              </label>
            )}
            <label className="field">
              <span><LockKeyhole size={14} /><b>Password</b></span>
              <div><input name="password" type="password" required /></div>
            </label>
            {error && <p className="form-error"><AlertCircle size={13} /> {error}</p>}
            <button className="primary-button full" disabled={loading}>
              {loading ? <><Loader2 size={14} className="spin" /> {signup ? 'Creating account…' : 'Signing in…'}</> : signup ? 'Sign Up' : 'Login'}
            </button>
          </form>
          <p className="form-subtitle">
            {signup
              ? <><span>Already have an account? </span><button onClick={() => go('login')}>Login</button></>
              : <><span>Don&apos;t have an account? </span><button onClick={() => go('signup')}>Sign Up</button></>
            }
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── App shell ────────────────────────────────────────────────────────────────

function AppShell({ children, view, go, profile, logout }: {
  children: React.ReactNode
  view: View
  go: (v: View) => void
  profile: ProfileData
  logout: () => void
}) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app-shell">
      <header className="app-header">
        <button className="mobile-menu" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu"><Menu size={20} /></button>
        <Logo onClick={() => go('dashboard')} />
        <div className="app-header-actions">
          <Bell size={18} className="bell-icon" />
          <div className="user-chip">
            <span>{profile.name[0]?.toUpperCase()}</span>
            <small><b>{profile.name}</b>Patient</small>
            <ChevronDown size={14} />
          </div>
        </div>
      </header>
      <div className="app-body">
        {menuOpen && <div className="sidebar-overlay" onClick={() => setMenuOpen(false)} />}
        <aside className={menuOpen ? 'sidebar open' : 'sidebar'}>
          <div className="sidebar-logo"><Stethoscope size={16} /> Clinico</div>
          {navItems.map(({ view: itemView, label, icon: Icon }) => (
            <button
              key={itemView}
              className={view === itemView ? 'nav-item active' : 'nav-item'}
              onClick={() => { go(itemView); setMenuOpen(false) }}
            >
              <Icon size={17} />{label}
            </button>
          ))}
          <button className="logout" onClick={logout}><LogOut size={17} />Logout</button>
        </aside>
        <main className="app-content">{children}</main>
      </div>
    </div>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function Dashboard({
  go,
  appointments,
  profile,
  onAction,
  onNewAppt,
}: {
  go: (v: View) => void
  appointments: AppointmentData[]
  profile: ProfileData
  onAction: (appt: AppointmentData, kind: 'cancel' | 'reschedule' | 'followup') => void
  onNewAppt: () => void
}) {
  const next = appointments.find(a => (a.status || '').toUpperCase() === 'BOOKED') ?? appointments[0]
  const bookedCount = appointments.filter(a => (a.status || '').toUpperCase() === 'BOOKED').length

  return (
    <>
      <PageHeading title={`Welcome Back, ${profile.name}! 👋`} copy="Here's an overview of your health journey." />
      <div className="stats-grid">
        <Stat icon={<CalendarDays />} title="Upcoming Appointments" value={String(bookedCount || appointments.length)} tone="blue" />
        <Stat icon={<FileText />} title="Total Documents" value="5" tone="green" />
        <Stat icon={<MessageCircle />} title="AI Conversations" value="12" tone="purple" />
      </div>
      <h2 className="section-title">Quick Actions</h2>
      <div className="quick-actions">
        <button type="button" onClick={onNewAppt}>
          <span className="icon-box blue"><CalendarDays /></span>
          <b>Book New Appointment</b>
          <small>Find and schedule with a doctor</small>
        </button>
        <button type="button" onClick={() => go('documents')}>
          <span className="icon-box green"><FileText /></span>
          <b>Upload Document</b>
          <small>Add your medical reports</small>
        </button>
        <button type="button" onClick={() => go('ai')}>
          <span className="icon-box purple"><MessageCircle /></span>
          <b>Chat with Clinico AI</b>
          <small>Get instant health assistance</small>
        </button>
      </div>
      {next && (
        <>
          <div className="section-title-row">
            <h2 className="section-title">Upcoming Appointment</h2>
            <button className="link-button" onClick={() => go('appointments')}>View All</button>
          </div>
          <ConnectedAppointmentCard appointment={next} onAction={(kind) => onAction(next, kind)} />
        </>
      )}
      {!next && appointments.length === 0 && (
        <div className="empty-state">
          <CalendarDays size={36} />
          <p>No upcoming appointments. Book one now!</p>
          <button className="primary-button small" onClick={onNewAppt}>Book with AI <ArrowRight size={14} /></button>
        </div>
      )}
    </>
  )
}

// ─── Appointments ─────────────────────────────────────────────────────────────

function ConnectedAppointmentCard({ appointment, onAction }: { appointment: AppointmentData; onAction: (kind: 'cancel' | 'reschedule' | 'followup') => void }) {
  const date = new Date(appointment.datetime)
  const isBooked = (appointment.status || '').toUpperCase() === 'BOOKED'
  const isCancelled = (appointment.status || '').toUpperCase() === 'CANCELLED'

  const canReschedule = appointment.can_reschedule ?? isBooked
  const canCancel = appointment.can_cancel ?? isBooked
  const canFollowup = appointment.can_followup ?? !isCancelled

  return (
    <div className="appointment-card">
      <div className="date-tile">
        <strong>{isNaN(date.getDate()) ? '—' : date.getDate()}</strong>
        <small>{isNaN(date.getTime()) ? '' : date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</small>
      </div>
      <div className="appointment-info">
        <b>{appointment.doctor_name}</b>
        <span>{appointment.department_name}</span>
        <small>
          {isNaN(date.getTime()) ? '' : `${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · `}
          <span className={`status-badge status-${(appointment.status || '').toLowerCase()}`}>{appointment.status}</span>
        </small>
      </div>
      <div className="appointment-actions">
        {canReschedule && <button type="button" onClick={() => onAction('reschedule')}>Reschedule</button>}
        {canCancel && <button type="button" className="danger" onClick={() => onAction('cancel')}>Cancel</button>}
        {canFollowup && <button type="button" onClick={() => onAction('followup')}>Follow Up</button>}
      </div>
    </div>
  )
}

function AppointmentsView({ appointments, loading, onNewAppt, onAction }: {
  appointments: AppointmentData[]
  loading: boolean
  onNewAppt: () => void
  onAction: (appt: AppointmentData, kind: 'cancel' | 'reschedule' | 'followup') => void
}) {
  const [tab, setTab] = useState<'upcoming' | 'past' | 'cancelled'>('upcoming')
  const filtered = appointments.filter(a => {
    const status = (a.status || '').toUpperCase()
    const apptDate = new Date(a.datetime)
    const isPast = !isNaN(apptDate.getTime()) && apptDate < new Date()
    if (tab === 'upcoming') return status === 'BOOKED' || (status !== 'CANCELLED' && !isPast)
    if (tab === 'past') return status === 'COMPLETED' || isPast
    return status === 'CANCELLED'
  })

  return (
    <>
      <PageHeading
        title="My Appointments"
        copy="Manage your appointments and follow-ups."
        action={<button className="primary-button" onClick={onNewAppt}><Plus size={16} /> New Appointment</button>}
      />
      <div className="tabs">
        <button className={tab === 'upcoming' ? 'selected' : ''} onClick={() => setTab('upcoming')}>Upcoming</button>
        <button className={tab === 'past' ? 'selected' : ''} onClick={() => setTab('past')}>Past</button>
        <button className={tab === 'cancelled' ? 'selected' : ''} onClick={() => setTab('cancelled')}>Cancelled</button>
      </div>
      {loading
        ? <div className="loading-row"><Loader2 size={20} className="spin" /> Loading appointments…</div>
        : filtered.length === 0
          ? <div className="empty-state"><CalendarDays size={32} /><p>No {tab} appointments.</p></div>
          : <div className="appointment-list">{filtered.map(a => <ConnectedAppointmentCard key={a.appointment_id ?? (a as any).id} appointment={a} onAction={(kind) => onAction(a, kind)} />)}</div>
      }
    </>
  )
}

// ─── AI Chat view ─────────────────────────────────────────────────────────────

const suggestions = [
  'Book an appointment',
  'Check my upcoming appointments',
  'Reschedule my next appointment',
  'What departments are available?',
  'Help me with a follow-up',
]

function ClinicoAIView({
  messages,
  loading,
  message,
  setMessage,
  onSend,
  onSuggestion,
  userInitial,
}: {
  messages: ChatMessage[]
  loading: boolean
  message: string
  setMessage: (v: string) => void
  onSend: () => void
  onSuggestion: (text: string) => void
  userInitial: string
}) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey && message.trim()) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <>
      <PageHeading title="Clinico AI" copy="Ask about appointments, reports, or book a visit." />
      <div className="ai-layout">
        {/* Chat panel */}
        <div className="chat-panel">
          <div className="chat-messages-area">
            {messages.length === 0 && (
              <div className="chat-welcome">
                <div className="chat-welcome-icon"><Bot size={28} /></div>
                <h3>Hello! I&apos;m Clinico AI</h3>
                <p>I can help you book appointments, check your schedule, reschedule, or answer health-related questions. How can I help you today?</p>
              </div>
            )}
            {messages.map(msg => (
              <ChatBubble key={msg.id} msg={msg} userInitial={userInitial} />
            ))}
            {loading && <AgentPipelineTrace />}
            <div ref={bottomRef} />
          </div>

          <div className="chat-input-area">
            <div className="chat-input">
              <input
                ref={inputRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Type your message…"
                disabled={loading}
                aria-label="Chat message input"
              />
              <button
                className="send-btn"
                onClick={onSend}
                disabled={loading || !message.trim()}
                aria-label="Send message"
              >
                {loading ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
              </button>
            </div>
            <p className="chat-hint">Press Enter to send · Clinico AI may make mistakes. Verify important health info.</p>
          </div>
        </div>

        {/* Suggestions sidebar */}
        <div className="suggestions">
          <h3><Sparkles size={13} /> Try these examples</h3>
          {suggestions.map((text) => (
            <button key={text} onClick={() => onSuggestion(text)} disabled={loading}>
              <Search size={12} />{text}
            </button>
          ))}
        </div>
      </div>
    </>
  )
}

// ─── Documents ────────────────────────────────────────────────────────────────

function Documents() {
  const [uploaded, setUploaded] = useState(false)
  return (
    <>
      <PageHeading title="Upload Medical Document" copy="Upload and manage your medical reports." />
      <div className="documents-layout">
        <div className="upload-zone">
          <Upload size={34} />
          <h3>{uploaded ? 'Document uploaded successfully ✓' : 'Drag and drop your file here'}</h3>
          <button onClick={() => setUploaded(true)}>or click to upload</button>
          <small>Supported formats: PDF, JPG, JPEG, PNG (Max 10MB)</small>
        </div>
        <div className="category-panel">
          <h3>Document Categories</h3>
          {['ECG Reports', 'Blood Test Reports', 'Urine Test Reports', 'X-Ray Reports', 'Prescription'].map((name, index) => (
            <div className="category" key={name}>
              <span>{index === 0 ? <Activity /> : index === 4 ? <LockKeyhole /> : <ClipboardList />}</span>
              {name}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

// ─── Profile ──────────────────────────────────────────────────────────────────

function Profile({ profile }: { profile: ProfileData }) {
  return (
    <>
      <PageHeading title="My Profile" copy="Manage your personal health information." />
      <div className="settings-card profile-card">
        <div className="profile-avatar">{profile.name[0]?.toUpperCase()}</div>
        <div className="profile-name">
          <h2>{profile.name}</h2>
          <p>Patient</p>
        </div>
        <button className="secondary-button">Edit Profile</button>
        <div className="profile-fields">
          <Field icon={<User />} label="Full Name" placeholder={profile.name} />
          <Field icon={<Mail />} label="Email Address" placeholder={profile.email} />
          <Field icon={<Phone />} label="Phone Number" placeholder={profile.phone || '+91 XXXXX XXXXX'} />
        </div>
      </div>
    </>
  )
}

// ─── Settings ─────────────────────────────────────────────────────────────────

function SettingsPage() {
  return (
    <>
      <PageHeading title="Settings" copy="Manage your account preferences and privacy." />
      <div className="settings-card">
        <SettingRow icon={<Bell />} title="Notifications" copy="Receive reminders for your appointments and updates." />
        <SettingRow icon={<LockKeyhole />} title="Privacy & Security" copy="Manage your password and account security." />
        <SettingRow icon={<CircleHelp />} title="Help & Support" copy="Get answers to common questions." />
      </div>
    </>
  )
}

// ─── Connected app (real backend) ─────────────────────────────────────────────

function ConnectedApp({ view, go, auth, profile, logout }: {
  view: View
  go: (view: View) => void
  auth: Auth
  profile: ProfileData
  logout: () => void
}) {
  const [appointments, setAppointments] = useState<AppointmentData[]>([])
  const [apptLoading, setApptLoading] = useState(false)
  const [globalError, setGlobalError] = useState('')

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [sessionId, setSessionId] = useState('')

  // ── load appointments ──────────────────────────────────────────────────────
  async function loadAppointments() {
    setApptLoading(true)
    try {
      const data = await api<{ history: AppointmentData[] }>('/appointments/history', auth.access_token)
      setAppointments(data.history)
    } catch (e) {
      setGlobalError(e instanceof Error ? e.message : 'Failed to load appointments')
    } finally {
      setApptLoading(false)
    }
  }

  useEffect(() => {
    if (view === 'appointments' || view === 'dashboard') loadAppointments()
  }, [view])

  // ── start guided chat session ─────────────────────────────────────────────
  async function startChatSession(intent?: string, appointmentId?: number | null) {
    try {
      setChatLoading(true)
      setMessages([])
      go('ai')

      const result = await api<{ session_id: string; message: string }>(
        '/chat/session/start',
        auth.access_token,
        {
          method: 'POST',
          body: JSON.stringify({
            intent: intent ?? null,
            appointment_id: appointmentId ?? null,
          }),
        }
      )

      setSessionId(result.session_id)
      if (result.message) {
        setMessages([mkMsg('ai', result.message)])
      }
    } catch (e) {
      setGlobalError(e instanceof Error ? e.message : 'Failed to start chat session')
    } finally {
      setChatLoading(false)
    }
  }

  // ── appointment actions (cancel/reschedule/followup) ──────────────────────
  async function appointmentAction(appt: AppointmentData, kind: 'cancel' | 'reschedule' | 'followup') {
    const intentMap: Record<'cancel' | 'reschedule' | 'followup', string> = {
      cancel: 'CANCEL_APPOINTMENT',
      reschedule: 'RESCHEDULE_APPOINTMENT',
      followup: 'FOLLOWUP_APPOINTMENT',
    }

    const apptId = appt.appointment_id ?? (appt as any).id
    const numericId = apptId != null ? Number(apptId) : null
    const intent = intentMap[kind]

    await startChatSession(intent, numericId)
  }

  // ── chat send ──────────────────────────────────────────────────────────────
  async function sendMessage(textOverride?: string) {
    const text = (textOverride ?? chatInput).trim()
    if (!text || chatLoading) return
    setChatInput('')
    setChatLoading(true)

    // Optimistically add user message
    const userMsg = mkMsg('user', text)
    setMessages(prev => [...prev, userMsg])

    try {
      let id = sessionId

      // Start a new session if none exists
      if (!id) {
        const opened = await api<{ session_id: string; message: string }>(
          '/chat/session/start',
          auth.access_token,
          { method: 'POST', body: '{}' }
        )
        id = opened.session_id
        setSessionId(id)
        // Show the AI greeting from session start
        if (opened.message) {
          setMessages(prev => [...prev, mkMsg('ai', opened.message)])
        }
      }

      // Send the actual reply
      const reply = await api<{ message: string; done: boolean }>(
        '/chat/session/reply',
        auth.access_token,
        { method: 'POST', body: JSON.stringify({ session_id: id, message: text }) }
      )

      setMessages(prev => [...prev, mkMsg('ai', reply.message)])

      // Session is done — clear session ID so next message starts fresh and refresh appointments
      if (reply.done) {
        setSessionId('')
        loadAppointments()
      }
      // If session has alternative_slots but is NOT done, the backend kept the session alive.
      // The sessionId is preserved automatically so the next message continues the same session.
    } catch (e) {
      const errText = e instanceof Error ? e.message : 'Something went wrong. Please try again.'
      setMessages(prev => [...prev, mkMsg('system', errText)])
    } finally {
      setChatLoading(false)
    }
  }

  function startNewChatToAI() {
    setSessionId('')
    setMessages([])
    go('ai')
  }

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <AppShell view={view} go={go} profile={profile} logout={logout}>
      {globalError && (
        <div className="global-error">
          <AlertCircle size={14} />
          {globalError}
          <button onClick={() => setGlobalError('')}><X size={12} /></button>
        </div>
      )}

      {view === 'dashboard' && (
        <Dashboard
          go={go}
          appointments={appointments}
          profile={profile}
          onAction={appointmentAction}
          onNewAppt={() => startChatSession('BOOK_APPOINTMENT')}
        />
      )}

      {view === 'appointments' && (
        <AppointmentsView
          appointments={appointments}
          loading={apptLoading}
          onNewAppt={() => startChatSession('BOOK_APPOINTMENT')}
          onAction={appointmentAction}
        />
      )}

      {view === 'ai' && (
        <ClinicoAIView
          messages={messages}
          loading={chatLoading}
          message={chatInput}
          setMessage={setChatInput}
          onSend={() => sendMessage()}
          onSuggestion={(text) => sendMessage(text)}
          userInitial={profile.name[0]?.toUpperCase() ?? 'P'}
        />
      )}

      {view === 'profile' && <Profile profile={profile} />}
      {view === 'documents' && <Documents />}
      {view === 'settings' && <SettingsPage />}
    </AppShell>
  )
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function ClinicoApp() {
  const [view, setView] = useState<View>('home')
  const [auth, setAuth] = useState<Auth | null>(null)
  const [profile, setProfile] = useState<ProfileData | null>(null)

  // Restore session from localStorage
  useEffect(() => {
    const raw = localStorage.getItem('clinico-auth')
    if (!raw) return
    const saved = JSON.parse(raw) as Auth
    api<ProfileData>('/auth/me', saved.access_token)
      .then((me) => { setAuth(saved); setProfile(me); setView('dashboard') })
      .catch(() => localStorage.removeItem('clinico-auth'))
  }, [])

  function signedIn(newAuth: Auth, me: ProfileData) {
    localStorage.setItem('clinico-auth', JSON.stringify(newAuth))
    setAuth(newAuth)
    setProfile(me)
  }

  function logout() {
    localStorage.removeItem('clinico-auth')
    setAuth(null)
    setProfile(null)
    setView('home')
  }

  if (view === 'home') return <Landing go={setView} />
  if (view === 'signup' || view === 'login') return <ConnectedAuth mode={view} go={setView} signedIn={signedIn} />
  return auth && profile
    ? <ConnectedApp view={view} go={setView} auth={auth} profile={profile} logout={logout} />
    : <Landing go={setView} />
}
