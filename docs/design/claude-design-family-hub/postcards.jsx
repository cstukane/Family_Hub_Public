// postcards.jsx — PostCard variations + shared tokens/icons
// Export everything to window for cross-script access

const T = {
  bgPage: '#091019', bgSurface: '#111a24', bgElevated: '#15202b', bgDeep: '#0c1016',
  textPrimary: '#ece4d9', textSecondary: '#8f98a4', textAccent: '#d7c5b1', textMuted: '#5e6874',
  lineMuted: 'rgba(193, 183, 169, 0.11)', borderWarm: 'rgba(205, 189, 171, 0.17)',
  accentGrad: 'linear-gradient(135deg, #c17a61, #e09f7f)',
  accentBorder: 'rgba(214, 167, 123, 0.48)',
};

const HeartIcon = ({ filled, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24"
    fill={filled ? '#cf6b67' : 'none'} stroke={filled ? '#cf6b67' : 'currentColor'} strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round"
      d="M4.318 6.318a4.5 4.5 0 016.364 0L12 7.636l1.318-1.318a4.5 4.5 0 116.364 6.364L12 21.364 4.318 12.682a4.5 4.5 0 010-6.364z" />
  </svg>
);
const ChatIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
  </svg>
);
const DotsIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <circle cx="5" cy="12" r="1.3" fill="#8f98a4" /><circle cx="12" cy="12" r="1.3" fill="#8f98a4" /><circle cx="19" cy="12" r="1.3" fill="#8f98a4" />
  </svg>
);

function Avatar({ seed = 'a', size = 38, warm = false }) {
  const hues = [18, 32, 200, 220, 45];
  const h = hues[seed.charCodeAt(0) % hues.length];
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: `radial-gradient(circle at 35% 30%, hsl(${h},32%,40%) 0%, hsl(${h+8},26%,22%) 55%, #121b26 100%)`,
      border: `1px solid rgba(193,183,169,0.14)`,
      boxShadow: warm ? '0 0 0 2.5px rgba(193,148,100,0.26)' : 'none',
    }} />
  );
}

function PostCanvas({ variant = 'dark' }) {
  if (variant === 'dark') return (
    <div style={{ width: '100%', aspectRatio: '4/3',
      background: 'radial-gradient(circle at 28% 20%, rgba(175,118,58,0.2), transparent 52%), #0b0f14',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 28 }}>
      <div style={{ color: '#f0e8dc', fontSize: '1.25rem', fontWeight: 300, lineHeight: 1.22,
        letterSpacing: '-0.03em', textAlign: 'center',
        filter: 'drop-shadow(0 2px 10px rgba(0,0,0,0.55))' }}>
        the quiet hours are the<br />most honest ones
      </div>
    </div>
  );
  if (variant === 'warm') return (
    <div style={{ width: '100%', aspectRatio: '16/10',
      background: 'linear-gradient(155deg, #2d1e12 0%, #4a2c18 45%, #1a0d07 100%)',
      display: 'flex', alignItems: 'flex-end', padding: '20px 22px' }}>
      <div style={{ color: '#f5e8d4', fontSize: '1rem', fontWeight: 300, lineHeight: 1.3,
        letterSpacing: '-0.02em', filter: 'drop-shadow(0 1px 6px rgba(0,0,0,0.6))' }}>
        still here. still grateful.
      </div>
    </div>
  );
  return (
    <div style={{ width: '100%', aspectRatio: '1/1',
      background: 'radial-gradient(ellipse at 30% 25%, rgba(238,230,218,0.95), transparent 55%), #eae4de',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 28 }}>
      <div style={{ color: '#1c1612', fontSize: '1.1rem', fontWeight: 400, lineHeight: 1.25,
        letterSpacing: '-0.025em', textAlign: 'center' }}>
        notice something<br />beautiful today
      </div>
    </div>
  );
}

// — V1: AIRY — more space, 2-line meta, 40px avatar, bigger action targets
function PostCardAiry() {
  const [liked, setLiked] = React.useState(false);
  const [count, setCount] = React.useState(12);
  const [open, setOpen] = React.useState(true);
  const toggle = () => { setLiked(l => !l); setCount(c => liked ? c - 1 : c + 1); };
  return (
    <div style={{ background: T.bgSurface, borderRadius: 16,
      border: '1px solid rgba(193,183,169,0.1)',
      boxShadow: '0 20px 48px rgba(1,4,9,0.2), inset 0 1px 0 rgba(255,248,240,0.03)',
      overflow: 'hidden', fontFamily: 'Poppins, sans-serif', color: T.textPrimary }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 15px 12px', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Avatar seed="q" size={40} />
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 500, color: T.textPrimary, lineHeight: 1.15 }}>quietobserver</div>
            <div style={{ fontSize: '0.7rem', color: T.textMuted, marginTop: 3 }}>3 hours ago</div>
          </div>
        </div>
        <button style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer' }}><DotsIcon /></button>
      </div>
      <div style={{ margin: '0 14px 12px', borderRadius: 13, overflow: 'hidden', border: '1px solid rgba(193,183,169,0.07)' }}>
        <PostCanvas variant="dark" />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '2px 10px', borderTop: `1px solid ${T.lineMuted}`, minHeight: 52 }}>
        <button onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '8px 10px', background: 'transparent', border: 'none', color: open ? T.textAccent : T.textSecondary, borderRadius: 10, minHeight: 44, cursor: 'pointer' }}>
          <ChatIcon size={21} /><span style={{ fontSize: '0.77rem', color: T.textMuted }}>4</span>
        </button>
        <button onClick={toggle} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '8px 10px', background: 'transparent', border: 'none', color: liked ? '#cf6b67' : T.textSecondary, borderRadius: 10, minHeight: 44, cursor: 'pointer' }}>
          <HeartIcon filled={liked} size={21} /><span style={{ fontSize: '0.77rem', color: liked ? '#b85a56' : T.textMuted }}>{count}</span>
        </button>
      </div>
      {open && <CommentAreaAiry />}
    </div>
  );
}

function CommentAreaAiry() {
  return (
    <div style={{ padding: '6px 14px 14px' }}>
      <CommentNodeAiry username="morninglight" text="This one landed." />
      <CommentNodeAiry username="between_lines" text="I feel this every time I open the app.">
        <CommentNodeAiry username="quietobserver" text="Exactly what I was hoping." depth={1} />
      </CommentNodeAiry>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10 }}>
        <Avatar seed="y" size={26} />
        <div style={{ flex: 1, padding: '8px 12px', borderRadius: 10, border: `1px solid ${T.borderWarm}`, background: 'rgba(12,16,19,0.5)', fontSize: '0.79rem', color: T.textMuted }}>Add a comment…</div>
      </div>
    </div>
  );
}

function CommentNodeAiry({ username, text, depth = 0, children }) {
  return (
    <div style={{ marginTop: 9, paddingLeft: depth > 0 ? 30 : 0 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <Avatar seed={username} size={depth > 0 ? 24 : 28} />
        <div style={{ flex: 1 }}>
          <div style={{ background: 'rgba(12,16,19,0.42)', borderRadius: 10, border: '1px solid rgba(193,183,169,0.07)', padding: '7px 10px' }}>
            <div style={{ fontSize: '0.74rem', fontWeight: 500, color: T.textAccent, marginBottom: 3 }}>{username}</div>
            <div style={{ fontSize: '0.81rem', color: T.textPrimary, lineHeight: 1.45 }}>{text}</div>
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}

// — V2: FOCUSED — minimal header, near edge-to-edge image, right-aligned actions
function PostCardFocused() {
  const [liked, setLiked] = React.useState(false);
  const [count, setCount] = React.useState(7);
  const [open, setOpen] = React.useState(false);
  const toggle = () => { setLiked(l => !l); setCount(c => liked ? c - 1 : c + 1); };
  return (
    <div style={{ background: T.bgSurface, borderRadius: 16,
      border: '1px solid rgba(205,189,171,0.11)',
      boxShadow: '0 16px 40px rgba(1,4,9,0.22)',
      overflow: 'hidden', fontFamily: 'Poppins, sans-serif', color: T.textPrimary }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px 10px', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <Avatar seed="m" size={34} />
          <span style={{ fontSize: '0.84rem', fontWeight: 500, color: T.textPrimary }}>morninglight</span>
          <span style={{ fontSize: '0.68rem', color: T.textMuted }}>2d</span>
        </div>
        <button style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer' }}><DotsIcon size={16} /></button>
      </div>
      <div style={{ margin: '0 10px', borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(193,183,169,0.06)' }}>
        <PostCanvas variant="warm" />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '4px 10px', gap: 2, minHeight: 50, borderTop: `1px solid ${T.lineMuted}` }}>
        <button onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px', background: 'transparent', border: 'none', color: open ? T.textAccent : T.textSecondary, borderRadius: 10, minHeight: 44, cursor: 'pointer' }}>
          <ChatIcon size={20} /><span style={{ fontSize: '0.74rem', color: T.textMuted }}>3</span>
        </button>
        <button onClick={toggle} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px', background: 'transparent', border: 'none', color: liked ? '#cf6b67' : T.textSecondary, borderRadius: 10, minHeight: 44, cursor: 'pointer' }}>
          <HeartIcon filled={liked} size={20} /><span style={{ fontSize: '0.74rem', color: liked ? '#b85a56' : T.textMuted }}>{count}</span>
        </button>
      </div>
      {open && (
        <div style={{ borderTop: `1px solid ${T.lineMuted}`, padding: '10px 14px 12px' }}>
          <FlatComment username="stillwater" text="This is what I needed today." />
          <FlatComment username="nightshore" text="Thank you for this." indent />
          <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
            <Avatar seed="y" size={24} />
            <input readOnly placeholder="Reply…" style={{ flex: 1, background: 'rgba(12,16,19,0.5)', border: `1px solid ${T.borderWarm}`, borderRadius: 20, padding: '7px 12px', fontSize: '0.79rem', color: T.textPrimary, outline: 'none', fontFamily: 'inherit' }} />
          </div>
        </div>
      )}
    </div>
  );
}

function FlatComment({ username, text, indent = false }) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginTop: 8, paddingLeft: indent ? 28 : 0 }}>
      <Avatar seed={username} size={indent ? 22 : 26} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: '0.74rem', fontWeight: 500, color: T.textAccent }}>{username}</span>
        <span style={{ fontSize: '0.74rem', color: T.textMuted, margin: '0 5px' }}>·</span>
        <span style={{ fontSize: '0.8rem', color: T.textPrimary }}>{text}</span>
      </div>
    </div>
  );
}

// — V3: WARM REFINED — warm avatar ring, pill-style actions, threaded comments w/ timestamps
function PostCardWarm() {
  const [liked, setLiked] = React.useState(true);
  const [count, setCount] = React.useState(18);
  const [open, setOpen] = React.useState(true);
  const toggle = () => { setLiked(l => !l); setCount(c => liked ? c - 1 : c + 1); };
  return (
    <div style={{ background: T.bgSurface, borderRadius: 18,
      border: '1px solid rgba(205,175,139,0.16)',
      boxShadow: '0 24px 56px rgba(1,4,9,0.22), inset 0 1px 0 rgba(255,242,220,0.04)',
      overflow: 'hidden', fontFamily: 'Poppins, sans-serif', color: T.textPrimary }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '15px 16px 13px', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
          <Avatar seed="b" size={40} warm />
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 500, color: T.textPrimary, lineHeight: 1.15 }}>between_lines</div>
            <div style={{ fontSize: '0.7rem', color: T.textMuted, marginTop: 3 }}>yesterday</div>
          </div>
        </div>
        <button style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer' }}><DotsIcon /></button>
      </div>
      <div style={{ margin: '0 14px 13px', borderRadius: 14, overflow: 'hidden', border: '1px solid rgba(193,183,169,0.08)' }}>
        <PostCanvas variant="light" />
      </div>
      <div style={{ display: 'flex', gap: 8, padding: '6px 14px 10px', borderTop: `1px solid ${T.lineMuted}` }}>
        <button onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 999, background: open ? 'rgba(193,183,169,0.08)' : 'transparent', border: `1px solid ${open ? 'rgba(193,183,169,0.2)' : 'transparent'}`, color: open ? T.textAccent : T.textSecondary, fontSize: '0.77rem', cursor: 'pointer', fontFamily: 'inherit', minHeight: 36, transition: 'all 150ms' }}>
          <ChatIcon size={15} /><span>6 comments</span>
        </button>
        <button onClick={toggle} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 999, background: liked ? 'rgba(207,107,103,0.1)' : 'transparent', border: `1px solid ${liked ? 'rgba(207,107,103,0.28)' : 'transparent'}`, color: liked ? '#d67874' : T.textSecondary, fontSize: '0.77rem', cursor: 'pointer', fontFamily: 'inherit', minHeight: 36, transition: 'all 150ms' }}>
          <HeartIcon filled={liked} size={15} /><span>{count} {liked ? 'liked' : 'like'}</span>
        </button>
      </div>
      {open && (
        <div style={{ padding: '4px 14px 14px', borderTop: `1px solid ${T.lineMuted}` }}>
          <ThreadedComment username="nightshore" text="I read this every morning." time="8h" />
          <ThreadedComment username="quietobserver" text="This deserves to be printed out." time="6h">
            <ThreadedComment username="between_lines" text="Maybe someday it will be ☁" time="5h" depth={1} />
          </ThreadedComment>
          <div style={{ display: 'flex', gap: 9, marginTop: 12, alignItems: 'center' }}>
            <Avatar seed="y" size={28} />
            <div style={{ flex: 1, padding: '9px 13px', borderRadius: 12, border: `1px solid ${T.borderWarm}`, background: 'rgba(12,16,19,0.45)', fontSize: '0.79rem', color: T.textMuted }}>Say something…</div>
          </div>
        </div>
      )}
    </div>
  );
}

function ThreadedComment({ username, text, time, depth = 0, children }) {
  return (
    <div style={{ marginTop: 10, paddingLeft: depth > 0 ? 30 : 0 }}>
      {depth > 0 && <div style={{ position: 'absolute', left: 14, top: 0, bottom: 0, width: 2, background: 'rgba(193,148,100,0.2)', borderRadius: 1 }} />}
      <div style={{ display: 'flex', gap: 9, position: 'relative' }}>
        <Avatar seed={username} size={depth > 0 ? 24 : 28} />
        <div style={{ flex: 1 }}>
          <div style={{ background: 'rgba(12,16,19,0.38)', borderRadius: 11, border: '1px solid rgba(193,183,169,0.07)', padding: '8px 11px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: '0.74rem', fontWeight: 500, color: T.textAccent }}>{username}</span>
              <span style={{ fontSize: '0.67rem', color: T.textMuted }}>{time}</span>
            </div>
            <div style={{ fontSize: '0.82rem', color: T.textPrimary, lineHeight: 1.45 }}>{text}</div>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { T, HeartIcon, ChatIcon, DotsIcon, Avatar, PostCanvas, PostCardAiry, PostCardFocused, PostCardWarm });
