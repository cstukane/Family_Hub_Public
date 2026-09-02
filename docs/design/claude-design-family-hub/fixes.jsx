// fixes.jsx — Sign-in, MobileNav, NotifTray, Settings — palette-unified

// === ICONS ===
const SunIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <circle cx="12" cy="12" r="4.2" />
    <path strokeLinecap="round" d="M12 2.5v1.8M12 19.7v1.8M4.22 4.22l1.28 1.28M18.5 18.5l1.28 1.28M2.5 12h1.8M19.7 12h1.8M4.22 19.78l1.28-1.28M18.5 5.5l1.28-1.28" />
  </svg>
);
const UserIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);
const ShieldIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l7 3v5c0 4.4-2.9 8.4-7 9.7C7.9 19.4 5 15.4 5 11V6l7-3z" />
  </svg>
);
const BellIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
);
const LogOutIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);
const HomeIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l9-9 9 9M5 10v10a1 1 0 001 1h4v-4h4v4h4a1 1 0 001-1V10" />
  </svg>
);
const ChatBubbleIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);
const ChevronRight = ({ open, size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 160ms ease' }}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6" />
  </svg>
);

// Field component reused across sign-in variants
function Field({ label, type, placeholder, focused, onFocus, onBlur }) {
  const { T } = window;
  return (
    <label style={{ display: 'block' }}>
      <div style={{ fontSize: '0.73rem', fontWeight: 500, color: T.textSecondary, marginBottom: 6, letterSpacing: '0.025em' }}>
        {label}
      </div>
      <input type={type} placeholder={placeholder} readOnly
        onFocus={onFocus} onBlur={onBlur}
        style={{
          width: '100%', padding: '10px 12px', borderRadius: 9,
          background: 'rgba(12,16,19,0.62)',
          border: `1px solid ${focused ? 'rgba(214,167,123,0.72)' : 'rgba(205,189,171,0.14)'}`,
          boxShadow: focused ? '0 0 0 3px rgba(214,167,123,0.1)' : 'none',
          color: T.textPrimary, fontSize: '0.87rem',
          fontFamily: 'Poppins, sans-serif', outline: 'none',
          transition: 'border-color 150ms, box-shadow 150ms',
          boxSizing: 'border-box',
        }}
      />
    </label>
  );
}

// === SIGN-IN V1 — CENTERED WARM MODAL ===
function SignInCentered() {
  const { T } = window;
  const [mode, setMode] = React.useState('signIn');
  const [focused, setFocused] = React.useState(null);
  return (
    <div style={{
      width: '100%', minHeight: 520,
      background: `radial-gradient(circle at 22% 14%, rgba(217,158,111,0.11), transparent 40%), #050911`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 28, fontFamily: 'Poppins, sans-serif', borderRadius: 18,
    }}>
      <div style={{
        width: '100%', maxWidth: 340,
        background: T.bgSurface,
        border: '1px solid rgba(205,189,171,0.22)',
        borderRadius: 18,
        boxShadow: '0 32px 80px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,242,220,0.04)',
        padding: '28px 26px 24px', color: T.textPrimary,
      }}>
        <div style={{ marginBottom: 22 }}>
          <div style={{ fontSize: '1.5rem', letterSpacing: '-0.04em', color: '#e6d7c3', fontWeight: 300, lineHeight: 1 }}>lowlight</div>
          <div style={{ marginTop: 8, fontSize: '0.88rem', color: T.textSecondary, fontWeight: 300 }}>
            {mode === 'signIn' ? 'Welcome back. You made it.' : "Welcome, you've found the way."}
          </div>
        </div>
        <div style={{ display: 'grid', gap: 14 }}>
          <Field label="Email" type="email" placeholder="you@somewhere.com" focused={focused === 'e'} onFocus={() => setFocused('e')} onBlur={() => setFocused(null)} />
          {mode === 'register' && <Field label="Username" type="text" placeholder="Choose a handle" focused={focused === 'u'} onFocus={() => setFocused('u')} onBlur={() => setFocused(null)} />}
          <Field label="Password" type="password" placeholder="••••••••" focused={focused === 'p'} onFocus={() => setFocused('p')} onBlur={() => setFocused(null)} />
        </div>
        {mode === 'signIn' && (
          <div style={{ textAlign: 'right', marginTop: 6 }}>
            <span style={{ fontSize: '0.71rem', color: T.textMuted, cursor: 'pointer' }}>Forgot password?</span>
          </div>
        )}
        <button style={{
          width: '100%', marginTop: 20, background: T.accentGrad,
          border: '1px solid rgba(241,185,149,0.5)', borderRadius: 10,
          padding: '11px 16px', color: '#fff8f0', fontSize: '0.9rem', fontWeight: 500,
          cursor: 'pointer', letterSpacing: '0.01em', fontFamily: 'inherit',
        }}>
          {mode === 'signIn' ? 'Sign In' : 'Create Account'}
        </button>
        <div style={{ marginTop: 14, textAlign: 'center', fontSize: '0.73rem', color: T.textMuted }}>
          {mode === 'signIn'
            ? <span>No account? <span style={{ color: T.textAccent, cursor: 'pointer' }} onClick={() => setMode('register')}>Join lowlight</span></span>
            : <span>Already here? <span style={{ color: T.textAccent, cursor: 'pointer' }} onClick={() => setMode('signIn')}>Sign in</span></span>}
        </div>
      </div>
    </div>
  );
}

// === SIGN-IN V2 — SIDE PANEL ===
function SignInPanel() {
  const { T } = window;
  const [mode, setMode] = React.useState('signIn');
  const [focused, setFocused] = React.useState(null);
  return (
    <div style={{
      width: '100%', minHeight: 520,
      background: '#060a0f', display: 'flex', alignItems: 'stretch',
      justifyContent: 'flex-end', fontFamily: 'Poppins, sans-serif',
      borderRadius: 18, overflow: 'hidden', position: 'relative',
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 28% 50%, rgba(193,148,100,0.07), transparent 62%)',
        display: 'flex', alignItems: 'center', paddingLeft: 28,
      }}>
        <div style={{ opacity: 0.16 }}>
          <div style={{ fontSize: '1.4rem', letterSpacing: '-0.04em', color: '#e6d7c3', fontWeight: 300 }}>lowlight</div>
          <div style={{ marginTop: 6, fontSize: '0.7rem', color: '#8f98a4', letterSpacing: '0.1em', textTransform: 'uppercase' }}>quiet. honest. here.</div>
        </div>
      </div>
      <div style={{
        width: 290, background: T.bgSurface,
        borderLeft: '1px solid rgba(205,189,171,0.18)',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '32px 24px', color: T.textPrimary, position: 'relative',
      }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 600, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#bfa98a', marginBottom: 8 }}>
            {mode === 'signIn' ? 'Welcome back' : 'Join us'}
          </div>
          <h2 style={{ margin: 0, fontSize: '1.55rem', letterSpacing: '-0.035em', fontWeight: 300, color: '#f0e4d4', lineHeight: 1.12 }}>
            {mode === 'signIn' ? 'Sign in to lowlight.' : 'Find your place.'}
          </h2>
        </div>
        <div style={{ display: 'grid', gap: 13 }}>
          <Field label="Email" type="email" placeholder="you@somewhere.com" focused={focused === 'e'} onFocus={() => setFocused('e')} onBlur={() => setFocused(null)} />
          {mode === 'register' && <Field label="Username" type="text" placeholder="Choose a handle" focused={focused === 'u'} onFocus={() => setFocused('u')} onBlur={() => setFocused(null)} />}
          <Field label="Password" type="password" placeholder="••••••••" focused={focused === 'p'} onFocus={() => setFocused('p')} onBlur={() => setFocused(null)} />
        </div>
        <button style={{
          width: '100%', marginTop: 18, background: T.accentGrad,
          border: '1px solid rgba(241,185,149,0.5)', borderRadius: 10,
          padding: '11px 14px', color: '#fff8f0', fontSize: '0.87rem', fontWeight: 500,
          cursor: 'pointer', fontFamily: 'inherit',
        }}>
          {mode === 'signIn' ? 'Sign In' : 'Create Account'}
        </button>
        <div style={{ marginTop: 14, fontSize: '0.72rem', color: T.textMuted }}>
          {mode === 'signIn'
            ? <span>No account? <span style={{ color: T.textAccent, cursor: 'pointer' }} onClick={() => setMode('register')}>Join lowlight</span></span>
            : <span>Already here? <span style={{ color: T.textAccent, cursor: 'pointer' }} onClick={() => setMode('signIn')}>Sign in</span></span>}
        </div>
      </div>
    </div>
  );
}

// === MOBILE NAV — FIXED ===
function MobileNavFixed() {
  const { T } = window;
  const [active, setActive] = React.useState('feed');
  const navItems = [
    { id: 'feed', label: 'Feed', Icon: HomeIcon },
    { id: 'chat', label: 'Chat', Icon: ChatBubbleIcon },
  ];
  return (
    <div style={{ fontFamily: 'Poppins, sans-serif' }}>
      <div style={{ fontSize: '0.65rem', color: T.textMuted, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>Before</div>
      <nav style={{ display: 'flex', background: '#1e1e1e', borderTop: '1px solid #374151', height: 52, borderRadius: 10, overflow: 'hidden', marginBottom: 20 }}>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRight: '1px solid #374151', color: 'white', fontSize: '0.88rem', fontFamily: 'Poppins, sans-serif' }}>Feed</div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: '0.88rem', fontFamily: 'Poppins, sans-serif' }}>Chat</div>
      </nav>
      <div style={{ fontSize: '0.65rem', color: T.textMuted, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>After</div>
      <nav style={{
        display: 'flex', background: 'rgba(11,17,24,0.97)',
        borderTop: `1px solid ${T.lineMuted}`, height: 60,
        borderRadius: 12, overflow: 'hidden',
        backdropFilter: 'blur(12px)',
      }}>
        {navItems.map(({ id, label, Icon }) => (
          <button key={id} onClick={() => setActive(id)} style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', gap: 4, background: 'transparent', border: 'none',
            cursor: 'pointer', position: 'relative',
            color: active === id ? T.textAccent : T.textMuted,
            transition: 'color 150ms', fontFamily: 'Poppins, sans-serif',
          }}>
            <Icon size={19} />
            <span style={{ fontSize: '0.63rem', letterSpacing: '0.02em' }}>{label}</span>
            {active === id && (
              <div style={{ position: 'absolute', bottom: 7, width: 18, height: 2, background: T.textAccent, borderRadius: 1 }} />
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}

// === NOTIFICATION TRAY — FIXED ===
function NotifTrayFixed() {
  const { T } = window;
  const items = [
    { label: 'Reply to your post', time: '2m', unread: true },
    { label: "Reply to your comment: 'still here…'", time: '1h', unread: true },
    { label: 'Reply to your post', time: '3h', unread: false },
  ];
  return (
    <div style={{ fontFamily: 'Poppins, sans-serif', color: T.textPrimary }}>
      <div style={{ fontSize: '0.65rem', color: T.textMuted, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 10 }}>Notification Tray</div>
      <div style={{
        background: 'rgba(18,23,32,0.98)', border: '1px solid rgba(205,189,171,0.16)',
        borderRadius: 16, boxShadow: '0 22px 60px rgba(0,0,0,0.45)', overflow: 'hidden',
      }}>
        {items.map((n, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', padding: '11px 14px', gap: 10,
            borderBottom: i < items.length - 1 ? `1px solid ${T.lineMuted}` : 'none',
            background: n.unread ? 'rgba(193,148,100,0.04)' : 'transparent',
            cursor: 'pointer',
          }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, background: n.unread ? '#c17a61' : 'transparent' }} />
            <span style={{ flex: 1, fontSize: '0.81rem', color: n.unread ? T.textPrimary : T.textSecondary, lineHeight: 1.4 }}>{n.label}</span>
            <span style={{ fontSize: '0.7rem', color: T.textMuted, whiteSpace: 'nowrap', flexShrink: 0 }}>{n.time}</span>
          </div>
        ))}
        <button style={{
          width: '100%', padding: '10px 14px', textAlign: 'left',
          background: 'transparent', border: 0, borderTop: `1px solid ${T.lineMuted}`,
          color: T.textMuted, fontSize: '0.79rem', cursor: 'pointer', fontFamily: 'Poppins, sans-serif',
        }}>
          Quiet all notices
        </button>
      </div>
    </div>
  );
}

// === SETTINGS CATEGORIES — SVG ICONS ADDED ===
function SettingsFixed() {
  const { T } = window;
  const [active, setActive] = React.useState('appearance');
  const cats = [
    { id: 'appearance', title: 'Appearance', desc: 'Theme, fonts, and how things feel', Icon: SunIcon, glyph: '☼' },
    { id: 'account', title: 'Account', desc: 'Your details and preferences', Icon: UserIcon, glyph: '♙' },
    { id: 'privacy', title: 'Privacy & Safety', desc: "Who sees what, and how you're protected", Icon: ShieldIcon, glyph: '♢' },
    { id: 'notifications', title: 'Notifications', desc: "Choose what you're notified about", Icon: BellIcon, glyph: '♧' },
    { id: 'logout', title: 'Log out', desc: 'Take a break anytime', Icon: LogOutIcon, glyph: '↪', danger: true },
  ];
  return (
    <div style={{ fontFamily: 'Poppins, sans-serif', color: T.textPrimary, display: 'grid', gap: 8 }}>
      {cats.map(({ id, title, desc, Icon, danger }) => {
        const isActive = active === id && !danger;
        return (
          <div key={id} onClick={() => !danger && setActive(id)} style={{
            borderRadius: 16, cursor: 'pointer', overflow: 'hidden',
            border: `1px solid ${isActive ? 'rgba(220,151,100,0.78)' : 'rgba(205,189,171,0.1)'}`,
            background: 'linear-gradient(145deg, rgba(22,27,32,0.88), rgba(13,18,23,0.76))',
            boxShadow: isActive ? '0 4px 20px rgba(0,0,0,0.18), inset 0 0 0 1px rgba(220,151,100,0.14)' : '0 2px 10px rgba(0,0,0,0.1)',
            transition: 'border-color 160ms',
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: '46px 1fr auto', alignItems: 'center', gap: 14, padding: '15px 18px' }}>
              <div style={{
                width: 42, height: 42, borderRadius: 13, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: danger ? 'rgba(181,96,82,0.12)' : 'rgba(193,148,100,0.1)',
                color: danger ? '#f19a83' : '#f1dfcf',
              }}>
                <Icon size={19} />
              </div>
              <div>
                <div style={{ fontSize: '0.98rem', fontWeight: 400, color: danger ? '#f19a83' : T.textPrimary, lineHeight: 1.2 }}>{title}</div>
                <div style={{ marginTop: 5, fontSize: '0.79rem', color: T.textMuted, lineHeight: 1.4 }}>{desc}</div>
              </div>
              {!danger && <ChevronRight open={isActive} size={14} />}
            </div>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, {
  SignInCentered, SignInPanel,
  MobileNavFixed, NotifTrayFixed, SettingsFixed,
  SunIcon, UserIcon, ShieldIcon, BellIcon, LogOutIcon, HomeIcon, ChatBubbleIcon,
});
