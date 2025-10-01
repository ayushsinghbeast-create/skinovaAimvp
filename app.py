import React, { useState, createContext, useContext, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

// --- Configuration and API Setup ---
// In a real production environment, you would use environment variables for this.
// For Vercel deployment, the backend will be hosted at the same domain under /api.
const API_BASE_URL = window.location.origin.includes('localhost')
  ? 'http://localhost:3001/api' // Development URL for backend
  : '/api'; // Production relative path

// --- Utility Functions and Hooks ---

// 1. Auth Context
const AuthContext = createContext();

const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(true);

  const authApi = useMemo(() => axios.create({ baseURL: API_BASE_URL }), []);

  useEffect(() => {
    if (token) {
      // Mock validation on initial load
      authApi.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      // In a real app, call a /api/verify endpoint to get user data
      setUser({
        id: 'user-123',
        email: 'mock@user.com',
        name: 'Alex Johnson',
        subscription: 'Premium',
        referralPoints: 120,
      });
    }
    setLoading(false);
  }, [token, authApi]);

  const login = useCallback(async (email, password) => {
    try {
      const response = await authApi.post('/login', { email, password });
      const { token, user } = response.data;
      localStorage.setItem('token', token);
      setToken(token);
      setUser(user);
      authApi.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, message: error.response?.data?.message || 'Login failed' };
    }
  }, [authApi]);

  const signup = useCallback(async (name, email, password) => {
    try {
      await authApi.post('/signup', { name, email, password });
      return { success: true };
    } catch (error) {
      console.error('Signup error:', error);
      return { success: false, message: error.response?.data?.message || 'Signup failed' };
    }
  }, [authApi]);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete authApi.defaults.headers.common['Authorization'];
  }, [authApi]);

  const value = useMemo(() => ({
    user, token, loading, login, signup, logout
  }), [user, token, loading, login, signup, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// 2. Theme Context
const ThemeContext = createContext();
const useTheme = () => useContext(ThemeContext);

const ThemeProvider = ({ children }) => {
  const [isDark, setIsDark] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme === 'dark';
  });

  const toggleTheme = useCallback(() => {
    setIsDark(prev => {
      const newTheme = !prev;
      localStorage.setItem('theme', newTheme ? 'dark' : 'light');
      return newTheme;
    });
  }, []);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const value = useMemo(() => ({ isDark, toggleTheme }), [isDark, toggleTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};


// 3. Simple Client-Side Router
const useRoutes = (routes, user, loading) => {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const navigate = useCallback((newPath) => {
    window.history.pushState({}, '', newPath);
    setPath(newPath);
  }, []);

  const currentRoute = useMemo(() => {
    let route = routes.find(r => r.path === path);
    if (!route) {
      // Check for path parameters (e.g., /forum/post-id)
      const pathSegments = path.split('/').filter(p => p);
      if (pathSegments.length === 3 && pathSegments[0] === 'forum') {
        route = routes.find(r => r.path === '/forum/:id');
        if (route) route.params = { id: pathSegments[2] };
      }
    }
    return route;
  }, [path, routes]);

  // Handle Authentication Redirects
  useEffect(() => {
    if (loading) return;

    if (!user && currentRoute && currentRoute.protected) {
      navigate('/login');
    } else if (user && (path === '/login' || path === '/signup' || path === '/')) {
      navigate('/dashboard');
    } else if (path === '/') {
      // Default route
      navigate('/login');
    }
  }, [user, loading, path, currentRoute, navigate]);

  return { path, navigate, currentRoute };
};


// 4. API Client for authenticated requests
const useApi = () => {
  const { token, logout } = useAuth();

  const api = useMemo(() => {
    const instance = axios.create({ baseURL: API_BASE_URL });

    instance.interceptors.request.use(config => {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    instance.interceptors.response.use(
      response => response,
      error => {
        if (error.response && error.response.status === 401) {
          // Token expired or invalid
          logout();
        }
        return Promise.reject(error);
      }
    );
    return instance;
  }, [token, logout]);

  return api;
};


// --- UI Components ---

const LoadingSpinner = ({ className = 'w-6 h-6' }) => (
  <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

const Skel = ({ className = 'h-6 w-full' }) => (
  <div className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg ${className}`}></div>
);

const NavItem = ({ to, icon, label, navigate, currentPath }) => {
  const isActive = currentPath === to;
  const baseClasses = 'flex items-center p-3 rounded-xl transition-all duration-300';
  const activeClasses = 'bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-200 shadow-md';
  const inactiveClasses = 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800';

  return (
    <motion.button
      onClick={() => navigate(to)}
      className={`${baseClasses} ${isActive ? activeClasses : inactiveClasses} w-full`}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <span className="text-xl mr-3">{icon}</span>
      <span className="font-medium">{label}</span>
    </motion.button>
  );
};

const Card = ({ children, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3 }}
  >
    {children}
  </motion.div>
);

const Sidebar = ({ navigate, path, user, logout }) => {
  const { isDark, toggleTheme } = useTheme();

  const navItems = [
    { to: '/dashboard', icon: '🏠', label: 'Dashboard' },
    { to: '/analyzer', icon: '🔍', label: 'Skin Analyzer' },
    { to: '/academy', icon: '📚', label: 'Academy' },
    { to: '/forum', icon: '💬', label: 'Community Forum' },
    { to: '/consult', icon: '👩‍⚕️', label: 'Consult Expert' },
    { to: '/pricing', icon: '💎', label: 'Subscription' },
    { to: '/referrals', icon: '🔗', label: 'Referrals' },
    { to: '/diet', icon: '🍎', label: 'Diet & Health' },
    { to: '/settings', icon: '⚙️', label: 'Settings' },
  ];

  return (
    <div className="fixed top-0 left-0 w-64 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 p-4 flex flex-col z-20 hidden md:flex">
      <div className="text-3xl font-extrabold text-blue-600 dark:text-blue-400 mb-8 p-2">
        SkinovaAi
      </div>
      <nav className="flex-grow space-y-2">
        {navItems.map(item => (
          <NavItem
            key={item.to}
            {...item}
            navigate={navigate}
            currentPath={path}
          />
        ))}
      </nav>
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-xl mb-3">
          <p className="font-semibold text-gray-800 dark:text-white truncate">{user?.name || 'Guest'}</p>
          <p className="text-sm text-blue-500 dark:text-blue-300">{user?.subscription || 'Free Plan'}</p>
        </div>
        <div className="flex justify-between items-center space-x-2">
          <motion.button
            onClick={toggleTheme}
            className="p-3 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:ring-2 ring-blue-400 transition-colors"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {isDark ? '☀️' : '🌙'}
          </motion.button>
          <motion.button
            onClick={logout}
            className="flex-grow p-3 rounded-xl bg-red-500 text-white font-semibold hover:bg-red-600 transition-colors shadow-lg"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Logout
          </motion.button>
        </div>
      </div>
    </div>
  );
};

const Header = ({ navigate }) => {
  const { user } = useAuth();
  return (
    <header className="sticky top-0 z-10 p-4 md:pl-72 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm shadow-md transition-colors duration-300">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white hidden sm:block">
          Welcome back, {user?.name.split(' ')[0] || 'User'}!
        </h1>
        <div className="md:hidden text-2xl font-extrabold text-blue-600 dark:text-blue-400">
          SkinovaAi
        </div>
        <motion.button
          onClick={() => navigate('/analyzer')}
          className="bg-blue-500 text-white font-semibold py-2 px-4 rounded-full shadow-lg hover:bg-blue-600 transition-all duration-300"
          whileHover={{ scale: 1.05, boxShadow: '0 4px 15px rgba(59, 130, 246, 0.5)' }}
          whileTap={{ scale: 0.95 }}
        >
          Quick Analysis 
        </motion.button>
      </div>
    </header>
  );
};

const PageContainer = ({ children, title }) => (
  <motion.div
    className="min-h-screen p-4 md:p-8 pt-20 md:pt-4"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    transition={{ duration: 0.4 }}
  >
    <h1 className="text-4xl font-extrabold mb-8 text-gray-900 dark:text-white hidden md:block">{title}</h1>
    {children}
  </motion.div>
);

// --- Page Components ---

// 1. Login/Signup Page
const LoginSignup = ({ navigate }) => {
  const { login, signup, loading } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [status, setStatus] = useState({ message: '', type: '' });
  const [submitLoading, setSubmitLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitLoading(true);
    setStatus({ message: '', type: '' });

    if (isLogin) {
      const result = await login(email, password);
      if (result.success) {
        setStatus({ message: 'Login successful! Redirecting...', type: 'success' });
        // Redirection handled by router hook
      } else {
        setStatus({ message: result.message, type: 'error' });
      }
    } else {
      const result = await signup(name, email, password);
      if (result.success) {
        setStatus({ message: 'Signup successful! Please login.', type: 'success' });
        setIsLogin(true);
        setName('');
      } else {
        setStatus({ message: result.message, type: 'error' });
      }
    }
    setSubmitLoading(false);
  };

  if (loading) return null; // Wait for initial auth check

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 p-4 transition-colors">
      <Card className="w-full max-w-md p-8">
        <div className="text-center">
          <h2 className="text-4xl font-extrabold text-blue-600 dark:text-blue-400 mb-2">
            SkinovaAi
          </h2>
          <p className="text-lg text-gray-600 dark:text-gray-300 mb-6">
            {isLogin ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6">
          {!isLogin && (
            <input
              type="text"
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-3 border border-gray-300 dark:border-gray-700 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-blue-500 focus:border-blue-500"
              required={!isLogin}
            />
          )}
          <input
            type="email"
            placeholder="Email Address (e.g., test@skinova.ai)"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-3 border border-gray-300 dark:border-gray-700 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-blue-500 focus:border-blue-500"
            required
          />
          <input
            type="password"
            placeholder="Password (e.g., 123456)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-3 border border-gray-300 dark:border-gray-700 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-blue-500 focus:border-blue-500"
            required
          />

          {status.message && (
            <motion.div
              className={`p-3 rounded-lg text-sm ${
                status.type === 'success'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200'
                  : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200'
              }`}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {status.message}
            </motion.div>
          )}

          <motion.button
            type="submit"
            className="w-full p-3 bg-blue-600 text-white rounded-xl font-bold shadow-md hover:bg-blue-700 transition-colors flex items-center justify-center"
            disabled={submitLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {submitLoading ? <LoadingSpinner className="w-5 h-5 text-white" /> : isLogin ? 'Login' : 'Signup'}
          </motion.button>
        </form>

        <p className="mt-6 text-center text-gray-600 dark:text-gray-400">
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <motion.button
            onClick={() => {
              setIsLogin(!isLogin);
              setStatus({ message: '', type: '' });
            }}
            className="text-blue-600 hover:text-blue-500 font-semibold"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {isLogin ? 'Sign up' : 'Login'}
          </motion.button>
        </p>
      </Card>
    </div>
  );
};

// 2. Dashboard Page
const Dashboard = ({ navigate }) => {
  const { user } = useAuth();
  const api = useApi();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch mock dashboard data from backend
        const res = await api.get('/dashboard');
        setData(res.data);
      } catch (error) {
        console.error('Dashboard fetch error:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [api]);

  const StatCard = ({ icon, title, value, onClick }) => (
    <Card className="flex flex-col items-center text-center p-4 cursor-pointer hover:ring-2 ring-blue-500 transition-all" onClick={onClick}>
      <span className="text-4xl mb-3">{icon}</span>
      <p className="text-xl font-bold text-gray-900 dark:text-white">{value}</p>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{title}</p>
    </Card>
  );

  const SectionTitle = ({ icon, title, link, navigate }) => (
    <div className="flex justify-between items-center mb-4">
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center">
        {icon} <span className="ml-2">{title}</span>
      </h2>
      {link && (
        <motion.button
          onClick={() => navigate(link)}
          className="text-blue-500 hover:text-blue-600 text-sm font-medium"
          whileHover={{ scale: 1.05 }}
        >
          View All &rarr;
        </motion.button>
      )}
    </div>
  );

  if (loading) {
    return (
      <PageContainer title="Dashboard">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => <Skel key={i} className="h-32" />)}
        </div>
        <Skel className="h-64 mb-6" />
        <Skel className="h-48" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Dashboard">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
        <StatCard icon="🔬" title="Last Analysis" value={data?.lastAnalysis || 'N/A'} onClick={() => navigate('/analyzer')} />
        <StatCard icon="🎓" title="Academy Progress" value={`${data?.academyProgress}%`} onClick={() => navigate('/academy')} />
        <StatCard icon="⭐" title="Referral Points" value={user?.referralPoints || 0} onClick={() => navigate('/referrals')} />
        <StatCard icon="🗓️" title="Upcoming Consult" value={data?.upcomingConsult || 'None'} onClick={() => navigate('/consult')} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card className="mb-6">
            <SectionTitle icon="💬" title="Trending Forum Questions" link="/forum" navigate={navigate} />
            <div className="space-y-4">
              {data?.trendingPosts?.slice(0, 3).map((post, index) => (
                <motion.div
                  key={index}
                  className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer transition-colors"
                  whileHover={{ x: 5 }}
                >
                  <p className="font-semibold text-gray-800 dark:text-white truncate">{post.title}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-300 mt-1">
                    {post.replies} replies | {post.upvotes} Upvotes
                  </p>
                </motion.div>
              ))}
            </div>
          </Card>
        </div>

        <div>
          <Card>
            <SectionTitle icon="🚀" title="Quick Actions" />
            <motion.button
              onClick={() => navigate('/analyzer')}
              className="w-full p-4 mb-3 bg-blue-500 text-white font-bold rounded-xl shadow-lg hover:bg-blue-600 transition-colors"
              whileHover={{ scale: 1.02 }}
            >
              Start New Analysis
            </motion.button>
            <motion.button
              onClick={() => navigate('/consult')}
              className="w-full p-4 bg-green-500 text-white font-bold rounded-xl shadow-lg hover:bg-green-600 transition-colors"
              whileHover={{ scale: 1.02 }}
            >
              Book an Expert
            </motion.button>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
};

// 3. Skin Analyzer Page
const SkinAnalyzer = () => {
  const api = useApi();
  const [image, setImage] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedHistory, setSelectedHistory] = useState(null);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.get('/analysis');
      setHistory(res.data.history.reverse());
      if (res.data.history.length > 0) {
        setAnalysisResult(res.data.history[res.data.history.length - 1]);
      }
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  }, [api]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(URL.createObjectURL(file));
      setSelectedHistory(null);
    }
  };

  const handleAnalyze = async () => {
    if (!image) return;

    setLoading(true);
    // Mock the AI analysis process
    const mockData = {
      date: new Date().toLocaleDateString(),
      skinType: ['Oily', 'Dry', 'Normal'][Math.floor(Math.random() * 3)],
      acneLevel: Math.floor(Math.random() * 5) + 1, // 1-5
      wrinkleLevel: Math.floor(Math.random() * 5) + 1, // 1-5
      recommendations: [
        { product: 'Gentle Cleanser', purpose: 'Daily wash' },
        { product: 'Hydrating Serum', purpose: 'Barrier repair' },
      ],
      score: Math.floor(Math.random() * 100),
    };

    try {
      const res = await api.post('/analysis', mockData);
      setAnalysisResult(res.data.newAnalysis);
      fetchHistory(); // Refresh history
      setImage(null);
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const AnalysisDisplay = ({ result }) => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <StatCard title="Skin Type" value={result.skinType} icon="💧" color="text-blue-500" />
        <StatCard title="Acne Level (1-5)" value={result.acneLevel} icon="🌶️" color="text-red-500" />
        <StatCard title="Wrinkle Level (1-5)" value={result.wrinkleLevel} icon="🕰️" color="text-yellow-500" />
        <StatCard title="Skin Score" value={`${result.score}/100`} icon="💯" color="text-green-500" />
      </div>

      <h3 className="text-xl font-semibold mt-6 text-gray-900 dark:text-white">Product Recommendations</h3>
      <ul className="space-y-2">
        {result.recommendations.map((rec, index) => (
          <li key={index} className="p-3 bg-blue-50 dark:bg-blue-900/50 rounded-xl flex justify-between items-center">
            <span className="font-medium text-gray-800 dark:text-gray-100">{rec.product}</span>
            <span className="text-sm text-blue-600 dark:text-blue-300">{rec.purpose}</span>
          </li>
        ))}
      </ul>
    </div>
  );

  const StatCard = ({ title, value, icon, color }) => (
    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl text-center">
      <p className="text-lg font-bold text-gray-900 dark:text-white">{value}</p>
      <p className="text-sm text-gray-500 dark:text-gray-300">{title}</p>
    </div>
  );

  return (
    <PageContainer title="Skin Analyzer">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Analysis Input */}
        <Card className="lg:col-span-1">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">New Skin Analysis</h2>
          <p className="mb-4 text-gray-500 dark:text-gray-400">Upload a clear photo of your face for AI analysis.</p>

          <div className="mb-6 relative h-64 border-2 border-dashed border-blue-300 dark:border-blue-700 rounded-xl flex flex-col items-center justify-center overflow-hidden">
            {image ? (
              <img src={image} alt="Upload Preview" className="h-full w-full object-cover" />
            ) : (
              <div className="text-center p-4">
                <p className="text-gray-500 dark:text-gray-400">Click to upload image</p>
              </div>
            )}
            <input
              type="file"
              accept="image/*"
              className="absolute inset-0 opacity-0 cursor-pointer"
              onChange={handleImageUpload}
            />
          </div>

          <motion.button
            onClick={handleAnalyze}
            disabled={!image || loading}
            className="w-full p-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-colors flex items-center justify-center disabled:opacity-50"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {loading ? <LoadingSpinner className="w-5 h-5 mr-2" /> : 'Run AI Analysis'}
          </motion.button>
          <div className="mt-4 p-3 bg-yellow-100 dark:bg-yellow-900/50 rounded-lg text-sm text-yellow-800 dark:text-yellow-200">
            Note: This feature uses mock AI data.
          </div>
        </Card>

        {/* Analysis Result */}
        <Card className="lg:col-span-2">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">
            {selectedHistory ? `Analysis from ${selectedHistory.date}` : 'Latest Analysis Result'}
          </h2>
          {loading && <Skel className="h-96" />}
          {!loading && analysisResult ? (
            <AnalysisDisplay result={selectedHistory || analysisResult} />
          ) : (
            !loading && <p className="text-gray-500 dark:text-gray-400">Upload a photo to start your first analysis!</p>
          )}
        </Card>
      </div>

      {/* History & Comparison */}
      <h2 className="text-3xl font-bold mt-12 mb-6 text-gray-900 dark:text-white">Analysis History</h2>
      <Card>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead>
              <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-300">
                <th className="px-6 py-3">Date</th>
                <th className="px-6 py-3">Type</th>
                <th className="px-6 py-3">Acne Level</th>
                <th className="px-6 py-3">Score</th>
                <th className="px-6 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {history.map((item, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{item.date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{item.skinType}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-red-500">{item.acneLevel}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-green-500">{item.score}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <motion.button
                      onClick={() => setSelectedHistory(item)}
                      className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-200 transition-colors"
                      whileHover={{ scale: 1.05 }}
                    >
                      View
                    </motion.button>
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan="5" className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">No analysis history found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </PageContainer>
  );
};

// 4. Academy Page
const Academy = () => {
  const api = useApi();
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Cleansing');
  const [quizScore, setQuizScore] = useState(null);

  useEffect(() => {
    const fetchLessons = async () => {
      try {
        const res = await api.get('/academy');
        setLessons(res.data.lessons);
      } catch (error) {
        console.error('Failed to fetch academy data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchLessons();
  }, [api]);

  const categories = ['Cleansing', 'Anti-aging', 'Acne-care', 'Diet', 'Mental Health'];

  const filteredLessons = useMemo(() => {
    return lessons.filter(lesson => lesson.category === activeTab);
  }, [lessons, activeTab]);

  const handleQuizSubmit = async (lessonId, score) => {
    try {
      setLoading(true);
      await api.post('/academy/quiz', { lessonId, score });
      setQuizScore({ lessonId, score });
      alert(`Quiz submitted! Your score: ${score}/5`);
    } catch (error) {
      console.error('Quiz submission failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const QuizComponent = ({ lesson }) => {
    const [answers, setAnswers] = useState({});
    const isCompleted = quizScore?.lessonId === lesson.id;

    const questions = [
      { q: 'What is the main function of a cleanser?', options: ['Hydration', 'Removal of dirt', 'UV protection'], correct: 'Removal of dirt' },
      { q: 'Which ingredient is best for anti-aging?', options: ['Water', 'Retinol', 'Alcohol'], correct: 'Retinol' },
      { q: 'Acne-prone skin should avoid which type of product?', options: ['Oil-free', 'Non-comedogenic', 'Heavy oils'], correct: 'Heavy oils' },
      { q: 'How often should you apply sunscreen?', options: ['Once a day', 'Every 2 hours', 'Only when sunny'], correct: 'Every 2 hours' },
      { q: 'What is the most important step in any routine?', options: ['Toner', 'Cleansing', 'Masking'], correct: 'Cleansing' }
    ];

    const handleSubmit = () => {
      let correctCount = 0;
      questions.forEach((q, index) => {
        if (answers[index] === q.correct) {
          correctCount++;
        }
      });
      handleQuizSubmit(lesson.id, correctCount);
    };

    return (
      <Card className="mt-4 p-4 border border-blue-200 dark:border-blue-800">
        <h4 className="text-xl font-bold mb-4 text-blue-600 dark:text-blue-400">Quiz: Test Your Knowledge!</h4>
        {isCompleted ? (
          <p className="text-green-600 dark:text-green-400 font-semibold">Quiz Completed! Score: {quizScore.score}/5</p>
        ) : (
          <div className="space-y-4">
            {questions.map((q, qIndex) => (
              <div key={qIndex}>
                <p className="font-medium text-gray-800 dark:text-white mb-2">{qIndex + 1}. {q.q}</p>
                <div className="flex flex-wrap gap-3">
                  {q.options.map(option => (
                    <motion.button
                      key={option}
                      onClick={() => setAnswers(prev => ({ ...prev, [qIndex]: option }))}
                      className={`p-2 rounded-lg text-sm transition-all ${
                        answers[qIndex] === option
                          ? 'bg-blue-500 text-white shadow-md'
                          : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-blue-100 dark:hover:bg-blue-800'
                      }`}
                      whileHover={{ scale: 1.05 }}
                    >
                      {option}
                    </motion.button>
                  ))}
                </div>
              </div>
            ))}
            <motion.button
              onClick={handleSubmit}
              className="w-full p-3 bg-green-500 text-white font-bold rounded-xl hover:bg-green-600 transition-colors mt-4"
              whileHover={{ scale: 1.02 }}
            >
              Submit Quiz
            </motion.button>
          </div>
        )}
      </Card>
    );
  };

  const LessonCard = ({ lesson }) => (
    <Card className="mb-4">
      <h3 className="text-xl font-bold mb-2 text-gray-900 dark:text-white">{lesson.title}</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{lesson.type}{lesson.duration}</p>

      {lesson.type === 'Video' && (
        <div className="aspect-video bg-black rounded-lg overflow-hidden mb-4">
          <iframe
            className="w-full h-full"
            src={lesson.content} // Mock YouTube Link
            title={lesson.title}
            frameBorder="0"
            allowFullScreen
          ></iframe>
        </div>
      )}

      {lesson.type === 'Article' && (
        <div className="prose dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 mb-4">
          <p className="font-medium text-lg">{lesson.content.split('\n')[0]}</p>
          <p className="text-sm line-clamp-3">{lesson.content.split('\n').slice(1).join(' ')}</p>
        </div>
      )}

      {lesson.quiz && <QuizComponent lesson={lesson} />}

      <div className="flex justify-end">
        <span className="text-sm font-semibold text-green-600 dark:text-green-400">
          {lesson.completed ? '✅ Completed' : '⏳ Pending'}
        </span>
      </div>
    </Card>
  );

  return (
    <PageContainer title="Academy (Learning Hub)">
      <Card className="mb-6">
        <h2 className="text-xl font-bold mb-2 text-gray-900 dark:text-white">Your Progress: 45% Complete</h2>
        <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
          <motion.div
            className="bg-blue-600 h-2.5 rounded-full"
            style={{ width: '45%' }}
            initial={{ width: 0 }}
            animate={{ width: '45%' }}
            transition={{ duration: 1 }}
          ></motion.div>
        </div>
      </Card>

      <div className="flex space-x-2 mb-6 overflow-x-auto pb-2">
        {categories.map(cat => (
          <motion.button
            key={cat}
            onClick={() => setActiveTab(cat)}
            className={`px-4 py-2 rounded-full font-semibold text-sm whitespace-nowrap transition-colors ${
              activeTab === cat
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-600'
            }`}
            whileHover={{ scale: 1.05 }}
          >
            {cat}
          </motion.button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-6">
          <Skel className="h-40" /><Skel className="h-40" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredLessons.length > 0 ? (
            filteredLessons.map(lesson => <LessonCard key={lesson.id} lesson={lesson} />)
          ) : (
            <p className="col-span-2 text-center text-gray-500 dark:text-gray-400">No lessons available in this category.</p>
          )}
        </div>
      )}
    </PageContainer>
  );
};

// 5. Community Forum Page
const ForumPostDetails = ({ postId, navigate }) => {
  const api = useApi();
  const { user } = useAuth();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [replyText, setReplyText] = useState('');

  const fetchPost = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(`/forum/post/${postId}`);
      setPost(res.data.post);
    } catch (error) {
      console.error('Failed to fetch post:', error);
    } finally {
      setLoading(false);
    }
  }, [api, postId]);

  useEffect(() => {
    fetchPost();
  }, [fetchPost]);

  const handleReply = async (e) => {
    e.preventDefault();
    if (!replyText.trim()) return;

    try {
      await api.post(`/forum/reply/${postId}`, {
        content: replyText,
      });
      setReplyText('');
      fetchPost(); // Refresh posts
    } catch (error) {
      console.error('Failed to post reply:', error);
    }
  };

  const handleUpvote = async (replyId) => {
    try {
      await api.post(`/forum/upvote/${replyId}`);
      fetchPost(); // Refresh to show updated upvotes
    } catch (error) {
      console.error('Failed to upvote:', error);
    }
  };

  if (loading) return <Skel className="h-96" />;
  if (!post) return <p className="text-red-500">Post not found.</p>;

  return (
    <Card className="lg:col-span-2">
      <motion.button onClick={() => navigate('/forum')} className="text-blue-500 mb-4 flex items-center" whileHover={{ x: -5 }}>
        &larr; Back to Forum
      </motion.button>
      <h1 className="text-3xl font-bold mb-3 text-gray-900 dark:text-white">{post.title}</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        Posted by {post.author} on {post.date} in <span className="font-semibold text-blue-500">{post.category}</span>
      </p>
      <div className="prose dark:prose-invert max-w-none mb-8 border-b pb-4">
        {post.content.split('\n').map((line, i) => <p key={i}>{line}</p>)}
      </div>

      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">{post.replies.length} Replies</h2>

      <div className="space-y-4 mb-8">
        {post.replies.map(reply => (
          <div key={reply.id} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl flex justify-between items-start">
            <div>
              <p className="font-medium text-gray-800 dark:text-white">{reply.content}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                - {reply.author} on {reply.date}
              </p>
            </div>
            <motion.button
              onClick={() => handleUpvote(reply.id)}
              className="flex items-center text-sm text-gray-500 dark:text-gray-400 hover:text-blue-500 transition-colors"
              whileHover={{ scale: 1.1 }}
            >
              {reply.upvotes}
            </motion.button>
          </div>
        ))}
      </div>

      <Card className="p-4 border border-green-200 dark:border-green-800">
        <h3 className="text-xl font-bold mb-3 text-green-600 dark:text-green-400">Post a Reply</h3>
        <form onSubmit={handleReply}>
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder={`Reply as ${user?.name}...`}
            className="w-full p-3 border border-gray-300 dark:border-gray-700 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-green-500 focus:border-green-500 min-h-[100px]"
            required
          />
          <motion.button
            type="submit"
            className="mt-3 p-3 bg-green-500 text-white rounded-xl font-bold hover:bg-green-600 transition-colors"
            whileHover={{ scale: 1.02 }}
          >
            Submit Reply
          </motion.button>
        </form>
      </Card>
    </Card>
  );
};

const Forum = ({ currentRoute, navigate }) => {
  const api = useApi();
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('All');
  const [searchTerm, setSearchTerm] = useState('');

  const categories = ['All', 'Acne', 'Anti-aging', 'Routine', 'Products', 'Diet'];

  const fetchPosts = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/forum');
      setPosts(res.data.posts);
    } catch (error) {
      console.error('Failed to fetch forum data:', error);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    if (!currentRoute.params) {
      fetchPosts();
    }
  }, [fetchPosts, currentRoute.params]);

  const filteredPosts = useMemo(() => {
    return posts.filter(post => {
      const categoryMatch = filter === 'All' || post.category === filter;
      const searchMatch = post.title.toLowerCase().includes(searchTerm.toLowerCase());
      return categoryMatch && searchMatch;
    });
  }, [posts, filter, searchTerm]);

  const PostListItem = ({ post }) => (
    <motion.div
      onClick={() => navigate(`/forum/post/${post.id}`)}
      className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl hover:bg-blue-50 dark:hover:bg-gray-600 transition-all cursor-pointer shadow-sm hover:shadow-md"
      whileHover={{ scale: 1.01 }}
    >
      <div className="flex justify-between items-start">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1 truncate">{post.title}</h3>
        <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded-full whitespace-nowrap">{post.category}</span>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2">{post.content.substring(0, 100)}...</p>
      <div className="flex justify-between items-center text-xs mt-2 text-gray-400 dark:text-gray-500">
        <span>{post.replies} Replies • {post.upvotes} Upvotes</span>
        <span>{post.author} • {post.date}</span>
      </div>
    </motion.div>
  );

  const CreatePostModal = ({ onClose }) => {
    const [title, setTitle] = useState('');
    const [content, setContent] = useState('');
    const [category, setCategory] = useState(categories[1]);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e) => {
      e.preventDefault();
      setSubmitting(true);
      try {
        await api.post('/forum', { title, content, category });
        fetchPosts();
        onClose();
      } catch (error) {
        console.error('Post creation failed:', error);
      } finally {
        setSubmitting(false);
      }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Create New Post</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              placeholder="Post Title (e.g. My T-zone is too oily)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white"
              required
            />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white"
            >
              {categories.slice(1).map(cat => <option key={cat} value={cat}>{cat}</option>)}
            </select>
            <textarea
              placeholder="What's your question? Be detailed..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white min-h-[150px]"
              required
            />
            <div className="flex justify-end space-x-3">
              <motion.button
                type="button"
                onClick={onClose}
                className="p-3 bg-gray-300 text-gray-800 rounded-xl font-bold hover:bg-gray-400 transition-colors"
                whileHover={{ scale: 1.02 }}
              >
                Cancel
              </motion.button>
              <motion.button
                type="submit"
                disabled={submitting}
                className="p-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-colors flex items-center"
                whileHover={{ scale: 1.02 }}
              >
                {submitting ? <LoadingSpinner className="w-5 h-5 mr-2" /> : 'Publish Question'}
              </motion.button>
            </div>
          </form>
        </Card>
      </div>
    );
  };

  const isPostView = currentRoute.params?.id;
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <PageContainer title="Community Forum">
      {isPostView ? (
        <ForumPostDetails postId={currentRoute.params.id} navigate={navigate} />
      ) : (
        <>
          {isModalOpen && <CreatePostModal onClose={() => setIsModalOpen(false)} />}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <Card className="lg:col-span-1 p-4">
              <h2 className="text-xl font-bold mb-3 text-gray-900 dark:text-white">Post Filters</h2>
              <div className="flex flex-wrap gap-2">
                {categories.map(cat => (
                  <motion.button
                    key={cat}
                    onClick={() => setFilter(cat)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      filter === cat
                        ? 'bg-blue-500 text-white shadow-md'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-blue-100 dark:hover:bg-gray-600'
                    }`}
                    whileHover={{ scale: 1.05 }}
                  >
                    {cat}
                  </motion.button>
                ))}
              </div>
              <input
                type="text"
                placeholder="Search posts..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full p-3 border border-gray-300 dark:border-gray-700 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-blue-500 focus:border-blue-500 mt-4"
              />
              <motion.button
                onClick={() => setIsModalOpen(true)}
                className="w-full mt-4 p-3 bg-green-500 text-white font-bold rounded-xl shadow-lg hover:bg-green-600 transition-colors"
                whileHover={{ scale: 1.02 }}
              >
                Ask a Question ✍️
              </motion.button>
            </Card>

            <Card className="lg:col-span-2 space-y-4">
              {loading ? (
                <div className="space-y-4">
                  <Skel className="h-20" /><Skel className="h-20" /><Skel className="h-20" />
                </div>
              ) : (
                <>
                  {filteredPosts.length > 0 ? (
                    filteredPosts.map(post => <PostListItem key={post.id} post={post} />)
                  ) : (
                    <p className="text-center text-gray-500 dark:text-gray-400 p-8">No posts match your filters or search term.</p>
                  )}
                </>
              )}
            </Card>
          </div>
        </>
      )}
    </PageContainer>
  );
};

// 6. Consult an Expert Page
const Consult = () => {
  const api = useApi();
  const { user } = useAuth();
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [type, setType] = useState('Video Call');
  const [notes, setNotes] = useState('');
  const [bookingStatus, setBookingStatus] = useState('');
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const isPremium = user?.subscription === 'Premium';

  const fetchBookings = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/consult');
      setBookings(res.data.bookings.reverse());
    } catch (error) {
      console.error('Failed to fetch bookings:', error);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    fetchBookings();
  }, [fetchBookings]);

  const handleBooking = async (e) => {
    e.preventDefault();
    if (!isPremium) {
      setBookingStatus('error: Only Premium users can book a consultation.');
      return;
    }

    try {
      setBookingStatus('loading');
      await api.post('/consult', { date, time, type, notes });
      setBookingStatus('success: Consultation booked successfully!');
      setDate(''); setTime(''); setType('Video Call'); setNotes('');
      fetchBookings();
    } catch (error) {
      setBookingStatus(`error: ${error.response?.data?.message || 'Booking failed.'}`);
    }
  };

  const BookingHistory = () => (
    <Card className="lg:col-span-2">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Booking History</h2>
      {loading ? (
        <Skel className="h-40" />
      ) : bookings.length > 0 ? (
        <div className="space-y-3">
          {bookings.map((booking, index) => (
            <div key={index} className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl flex justify-between items-center">
              <div>
                <p className="font-semibold text-gray-800 dark:text-white">{booking.date} at {booking.time}</p>
                <p className="text-sm text-blue-500 dark:text-blue-300">{booking.type} with Dr. Mock</p>
              </div>
              <span className="text-sm text-green-600 dark:text-green-400 font-medium">Confirmed</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 dark:text-gray-400">No past bookings found.</p>
      )}
    </Card>
  );

  const MockChat = () => (
    <Card className="lg:col-span-1 flex flex-col h-[400px]">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Premium Live Chat</h2>
      {isPremium ? (
        <div className="flex-grow flex flex-col border border-gray-200 dark:border-gray-700 rounded-xl p-3">
          <div className="flex-grow space-y-3 overflow-y-auto mb-3">
            <div className="flex justify-start"><div className="bg-blue-100 dark:bg-blue-900 p-3 rounded-t-xl rounded-r-xl max-w-[70%]">Hi! How can I help with your skin today? - Derm</div></div>
            <div className="flex justify-end"><div className="bg-green-100 dark:bg-green-900 p-3 rounded-t-xl rounded-l-xl max-w-[70%]">My acne has flared up recently.</div></div>
          </div>
          <input type="text" placeholder="Type your message..." className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white" />
        </div>
      ) : (
        <div className="text-center p-8 bg-red-50 dark:bg-red-900/50 rounded-lg">
          <p className="text-red-700 dark:text-red-200 font-semibold">
            🔓 Upgrade to **Premium** to access 24/7 Live Dermatologist Chat.
          </p>
        </div>
      )}
    </Card>
  );

  return (
    <PageContainer title="Consult an Expert">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Booking Form */}
        <Card className="lg:col-span-1">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Book a Consultation</h2>
          {!isPremium && (
            <div className="p-3 mb-4 bg-red-100 dark:bg-red-900/50 rounded-lg text-red-700 dark:text-red-200 font-semibold">
              ⚠️ Only Premium users can book. Please upgrade!
            </div>
          )}
          <form onSubmit={handleBooking} className="space-y-4">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white"
              required
              min={new Date().toISOString().split('T')[0]}
              disabled={!isPremium}
            />
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white"
              required
              disabled={!isPremium}
            />
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white"
              disabled={!isPremium}
            >
              <option>Video Call</option>
              <option>Chat</option>
            </select>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notes on your concerns..."
              className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white min-h-[100px]"
              disabled={!isPremium}
            />
            <motion.button
              type="submit"
              disabled={!isPremium || bookingStatus === 'loading'}
              className="w-full p-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center"
              whileHover={{ scale: 1.02 }}
            >
              {bookingStatus === 'loading' ? <LoadingSpinner className="w-5 h-5 mr-2" /> : 'Confirm Booking'}
            </motion.button>
            {bookingStatus && bookingStatus !== 'loading' && (
              <motion.div
                className={`p-3 rounded-lg text-sm ${bookingStatus.startsWith('success') ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200'}`}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {bookingStatus.split(': ')[1]}
              </motion.div>
            )}
          </form>
        </Card>

        {/* Live Chat & History */}
        <div className="lg:col-span-2 space-y-8">
          <MockChat />
          <BookingHistory />
        </div>
      </div>
    </PageContainer>
  );
};

// 7. Subscription & Monetization Page
const Pricing = ({ navigate }) => {
  const { user } = useAuth();
  const api = useApi();
  const [coupon, setCoupon] = useState('');
  const [couponStatus, setCouponStatus] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const plans = [
    { name: 'Free', price: '0', period: 'Forever', features: ['Limited Analysis', 'Basic Academy Access', 'View Forum'], isCurrent: user?.subscription === 'Free' || !user?.subscription },
    { name: 'Pro', price: '9.99', period: 'mo', features: ['Full Academy', 'Forum Posting & Voting', 'Comparison Analysis'], isCurrent: user?.subscription === 'Pro' },
    { name: 'Premium', price: '29.99', period: 'mo', features: ['All Pro Features', 'Expert Consultation', 'AI Future Skin Prediction (Mock)', '24/7 Live Chat'], isCurrent: user?.subscription === 'Premium' },
  ];

  const handleApplyCoupon = async () => {
    if (!coupon.trim()) return;
    try {
      const res = await api.post('/payments/coupon', { code: coupon });
      setCouponStatus({ success: true, discount: res.data.discount });
    } catch (error) {
      setCouponStatus({ success: false, message: error.response?.data?.message || 'Invalid code' });
    }
  };

  const handleMockPayment = async (planName, price) => {
    if (planName === 'Free') return;

    setIsProcessing(true);
    // Mock Stripe Sandbox payment processing
    try {
      const discount = couponStatus?.success ? couponStatus.discount : 0;
      const finalPrice = (price * (1 - discount / 100)).toFixed(2);
      await api.post('/payments/checkout', { plan: planName, price: finalPrice, coupon: couponStatus?.success ? coupon : null });

      // Update local state and refresh (in a real app, this would come from the backend)
      alert(`Mock payment successful for ${planName} ($${finalPrice})! You are now a ${planName} user.`);
      window.location.reload(); // Simple way to force re-auth check in mock env
    } catch (error) {
      alert(`Mock payment failed: ${error.response?.data?.message || 'Error processing payment.'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const PricingCard = ({ plan }) => (
    <Card className={`text-center p-6 flex flex-col ${plan.isCurrent ? 'ring-4 ring-blue-500' : ''}`}>
      <h3 className="text-2xl font-bold mb-2 text-gray-900 dark:text-white">{plan.name}</h3>
      <p className="text-gray-500 dark:text-gray-400 mb-6">{plan.name} plan unlocks essential features.</p>
      <div className="flex-grow">
        <p className="text-5xl font-extrabold text-blue-600 dark:text-blue-400 mb-2">
          ${plan.price}
          <span className="text-lg font-medium text-gray-500 dark:text-gray-400">/{plan.period}</span>
        </p>
        <ul className="text-left space-y-2 mb-8">
          {plan.features.map((feature, index) => (
            <li key={index} className="flex items-center text-gray-700 dark:text-gray-300">
              <span className="text-green-500 mr-2">✓</span> {feature}
            </li>
          ))}
        </ul>
      </div>

      <motion.button
        onClick={() => handleMockPayment(plan.name, parseFloat(plan.price))}
        disabled={plan.isCurrent || plan.name === 'Free' || isProcessing}
        className={`w-full p-3 rounded-xl font-bold transition-colors ${
          plan.isCurrent
            ? 'bg-gray-400 text-white'
            : plan.name === 'Free'
            ? 'bg-gray-200 text-gray-700'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
        whileHover={{ scale: plan.isCurrent || plan.name === 'Free' ? 1 : 1.02 }}
        whileTap={{ scale: plan.isCurrent || plan.name === 'Free' ? 1 : 0.98 }}
      >
        {plan.isCurrent ? 'Current Plan' : plan.name === 'Free' ? 'Current Plan' : isProcessing ? <LoadingSpinner className="w-5 h-5 mx-auto" /> : 'Get Started'}
      </motion.button>
    </Card>
  );

  return (
    <PageContainer title="Subscription Plans">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {plans.map(plan => <PricingCard key={plan.name} plan={plan} />)}
      </div>

      <Card className="mt-12 max-w-lg mx-auto">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Have a Discount Code?</h2>
        <div className="flex space-x-3">
          <input
            type="text"
            placeholder="Enter Code (e.g., SKIN20)"
            value={coupon}
            onChange={(e) => { setCoupon(e.target.value); setCouponStatus(null); }}
            className="flex-grow p-3 border rounded-lg dark:bg-gray-700 dark:text-white"
          />
          <motion.button
            onClick={handleApplyCoupon}
            className="p-3 bg-green-500 text-white rounded-xl font-bold hover:bg-green-600 transition-colors"
            whileHover={{ scale: 1.02 }}
          >
            Apply
          </motion.button>
        </div>
        {couponStatus && (
          <motion.div
            className={`mt-4 p-3 rounded-lg text-sm ${couponStatus.success ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200'}`}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {couponStatus.success ? `Success! ${couponStatus.discount}% discount applied.` : `Error: ${couponStatus.message}`}
          </motion.div>
        )}
      </Card>
    </PageContainer>
  );
};

// 8. Referral & Rewards Page
const Referrals = () => {
  const { user } = useAuth();
  const api = useApi();
  const [rewards, setRewards] = useState([]);
  const [loading, setLoading] = useState(true);

  const referralLink = `${window.location.origin}/signup?ref=${user?.id || 'YOURCODE'}`;

  useEffect(() => {
    const fetchRewards = async () => {
      try {
        const res = await api.get('/referrals');
        setRewards(res.data.rewards);
      } catch (error) {
        console.error('Failed to fetch rewards:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchRewards();
  }, [api]);

  const handleCopy = () => {
    navigator.clipboard.writeText(referralLink);
    alert('Referral link copied to clipboard!');
  };

  const handleRedeem = async (reward) => {
    if (user.referralPoints < reward.points) return;
    try {
      await api.post('/referrals/redeem', { rewardId: reward.id });
      alert(`Successfully redeemed ${reward.name}! Points deducted.`);
      window.location.reload(); // Simple mock refresh
    } catch (error) {
      alert(`Redemption failed: ${error.response?.data?.message || 'Error.'}`);
    }
  };

  return (
    <PageContainer title="Referral & Rewards">
      <Card className="mb-8 p-6 text-center bg-blue-50 dark:bg-blue-900/50">
        <h2 className="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-2">{user?.referralPoints || 0} Points</h2>
        <p className="text-xl text-gray-700 dark:text-gray-300">Your total earned referral points.</p>
      </Card>

      <Card className="mb-8">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Share & Earn</h2>
        <p className="mb-4 text-gray-600 dark:text-gray-400">
          Share your unique link with friends. You earn **50 points** for every successful signup!
        </p>
        <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
          <input
            type="text"
            readOnly
            value={referralLink}
            className="flex-grow p-3 border rounded-xl dark:bg-gray-700 dark:text-white text-sm truncate"
          />
          <motion.button
            onClick={handleCopy}
            className="p-3 bg-green-500 text-white rounded-xl font-bold hover:bg-green-600 transition-colors"
            whileHover={{ scale: 1.02 }}
          >
            Copy Link 📋
          </motion.button>
        </div>
      </Card>

      <h2 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white">Available Rewards</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          [...Array(3)].map((_, i) => <Skel key={i} className="h-40" />)
        ) : (
          rewards.map(reward => (
            <Card key={reward.id} className="p-5 flex flex-col justify-between">
              <div>
                <span className="text-4xl block mb-3">{reward.icon}</span>
                <h3 className="text-xl font-bold mb-1 text-gray-900 dark:text-white">{reward.name}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{reward.description}</p>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold text-blue-600 dark:text-blue-400">{reward.points} Pts</span>
                <motion.button
                  onClick={() => handleRedeem(reward)}
                  disabled={user?.referralPoints < reward.points}
                  className="p-2 bg-yellow-500 text-white rounded-lg font-bold hover:bg-yellow-600 transition-colors disabled:opacity-50"
                  whileHover={{ scale: 1.05 }}
                >
                  Redeem
                </motion.button>
              </div>
            </Card>
          ))
        )}
      </div>
    </PageContainer>
  );
};

// 9. Diet & Mental Health Page
const DietHealth = () => {
  const api = useApi();
  const [dietPlan, setDietPlan] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDiet = async () => {
      try {
        const res = await api.get('/diet');
        setDietPlan(res.data.plan);
      } catch (error) {
        console.error('Failed to fetch diet plan:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchDiet();
  }, [api]);

  const HealthInput = () => {
    const [age, setAge] = useState(30);
    const [skinGoal, setSkinGoal] = useState('Anti-inflammatory');

    return (
      <Card className="mb-8">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Health Data Input</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Age</label>
            <input type="number" value={age} onChange={(e) => setAge(e.target.value)} className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white" />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Skin Goal</label>
            <select value={skinGoal} onChange={(e) => setSkinGoal(e.target.value)} className="w-full p-3 border rounded-lg dark:bg-gray-700 dark:text-white">
              <option>Anti-inflammatory</option>
              <option>Hydration Boost</option>
              <option>Acne Reduction</option>
              <option>Collagen Support</option>
            </select>
          </div>
        </div>
        <motion.button
          onClick={() => alert('Mock update successful! Diet plan is generated based on these inputs.')}
          className="mt-4 w-full p-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-colors"
          whileHover={{ scale: 1.02 }}
        >
          Generate Personalized Plan
        </motion.button>
      </Card>
    );
  };

  const DietSection = () => (
    <Card className="lg:col-span-2">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Your Skin-Boosting Diet Plan</h2>
      {loading ? (
        <Skel className="h-64" />
      ) : (
        <div className="space-y-6">
          <p className="text-lg font-medium text-gray-800 dark:text-gray-200">
            {dietPlan.summary}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {dietPlan.focusAreas.map((area, index) => (
              <div key={index} className="p-4 bg-green-50 dark:bg-green-900/50 rounded-xl">
                <h3 className="font-bold text-green-700 dark:text-green-300 mb-1">{area.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-300">{area.foods}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );

  const MentalHealthSection = () => {
    const videos = [
      { title: '10 Min Stress Relief Meditation', url: 'https://www.youtube.com/embed/inpL2JdKj8o' },
      { title: 'Deep Sleep Music for Stress', url: 'https://www.youtube.com/embed/5R8v-o2LhC0' },
    ];
    return (
      <Card className="lg:col-span-1">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Mental Health & Stress</h2>
        <p className="mb-4 text-gray-600 dark:text-gray-400">
          Stress directly impacts skin health. Take a break with these embedded sessions.
        </p>
        <div className="space-y-4">
          {videos.map(video => (
            <div key={video.title} className="aspect-video bg-black rounded-lg overflow-hidden shadow-lg">
              <iframe
                className="w-full h-full"
                src={video.url}
                title={video.title}
                frameBorder="0"
                allowFullScreen
              ></iframe>
            </div>
          ))}
        </div>
      </Card>
    );
  };

  return (
    <PageContainer title="Diet & Mental Health">
      <HealthInput />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <DietSection />
        <MentalHealthSection />
      </div>
    </PageContainer>
  );
};

// 10. Settings & Profile Page
const Settings = () => {
  const { user } = useAuth();
  const { isDark, toggleTheme } = useTheme();

  const [voiceTip, setVoiceTip] = useState('');
  const [voiceLoading, setVoiceLoading] = useState(false);

  const handleVoiceTip = async () => {
    setVoiceLoading(true);
    // Mock AI Voice Tip generation
    await new Promise(resolve => setTimeout(resolve, 1500));
    setVoiceTip('Remember to double cleanse at night to fully remove sunscreen and pollution particles!');
    setVoiceLoading(false);
  };

  return (
    <PageContainer title="Settings & Profile">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Profile Info */}
        <Card className="lg:col-span-1">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Profile Information</h2>
          <div className="space-y-3">
            <p className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
              <span className="block text-xs text-gray-500 dark:text-gray-400">Name</span>
              <span className="font-semibold text-gray-900 dark:text-white">{user?.name}</span>
            </p>
            <p className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
              <span className="block text-xs text-gray-500 dark:text-gray-400">Email</span>
              <span className="font-semibold text-gray-900 dark:text-white">{user?.email}</span>
            </p>
            <p className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <span className="block text-xs text-blue-600 dark:text-blue-400">Subscription Plan</span>
              <span className="font-bold text-blue-800 dark:text-blue-200">{user?.subscription}</span>
            </p>
          </div>
        </Card>

        {/* App Settings */}
        <Card className="lg:col-span-2">
          <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">App Settings</h2>

          <div className="flex justify-between items-center p-4 border-b dark:border-gray-700">
            <span className="text-lg font-medium text-gray-800 dark:text-gray-200">Dark Mode</span>
            <motion.button
              onClick={toggleTheme}
              className={`p-2 rounded-full w-14 h-8 flex items-center transition-colors ${isDark ? 'bg-blue-600 justify-end' : 'bg-gray-300 justify-start'}`}
              whileTap={{ scale: 0.95 }}
            >
              <span className="block w-6 h-6 bg-white rounded-full shadow-md"></span>
            </motion.button>
          </div>

          <div className="p-4 border-b dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-2">Voice-based Skin Tips</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">Record your voice to receive personalized skincare advice.</p>
            <motion.button
              onClick={handleVoiceTip}
              disabled={voiceLoading}
              className="p-3 bg-purple-500 text-white rounded-xl font-bold hover:bg-purple-600 transition-colors flex items-center"
              whileHover={{ scale: 1.02 }}
            >
              {voiceLoading ? <LoadingSpinner className="w-5 h-5 mr-2" /> : 'Start Recording 🎤'}
            </motion.button>
            {voiceTip && (
              <motion.p
                className="mt-3 p-3 bg-purple-100 dark:bg-purple-900/50 rounded-lg text-purple-700 dark:text-purple-200"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                **AI Tip:** {voiceTip}
              </motion.p>
            )}
          </div>

          <div className="p-4">
            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-2">Future AR Try-On</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">A placeholder for future augmented reality product try-on features.</p>
            <motion.button
              disabled
              className="mt-3 p-3 bg-gray-300 text-gray-700 rounded-xl font-bold"
              whileHover={{ scale: 1.02 }}
            >
              Launch AR (Coming Soon)
            </motion.button>
          </div>
        </Card>
      </div>
    </PageContainer>
  );
};


// --- Main Layout and Router ---

const AppContent = () => {
  const { user, loading } = useAuth();

  const routes = useMemo(() => [
    { path: '/login', component: LoginSignup, protected: false },
    { path: '/signup', component: LoginSignup, protected: false },
    { path: '/dashboard', component: Dashboard, protected: true },
    { path: '/analyzer', component: SkinAnalyzer, protected: true },
    { path: '/academy', component: Academy, protected: true },
    { path: '/forum', component: Forum, protected: true },
    { path: '/forum/post/:id', component: Forum, protected: true },
    { path: '/consult', component: Consult, protected: true },
    { path: '/pricing', component: Pricing, protected: true },
    { path: '/referrals', component: Referrals, protected: true },
    { path: '/diet', component: DietHealth, protected: true },
    { path: '/settings', component: Settings, protected: true },
  ], []);

  const { path, navigate, currentRoute } = useRoutes(routes, user, loading);

  if (loading || (!user && path !== '/login' && path !== '/signup')) {
    // Initial loading or redirecting unauthorized user
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <LoadingSpinner className="w-10 h-10 text-blue-500" />
      </div>
    );
  }

  const PageComponent = currentRoute?.component;

  if (path === '/login' || path === '/signup' || !user) {
    return <LoginSignup navigate={navigate} />;
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <Sidebar navigate={navigate} path={path} user={user} logout={useAuth().logout} />
      <div className="flex-grow md:ml-64">
        <Header navigate={navigate} />
        <main>
          <AnimatePresence mode="wait">
            {PageComponent && (
              <motion.div key={path}>
                <PageComponent navigate={navigate} currentRoute={currentRoute} />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
      {/* Mobile Nav Overlay */}
      <div className="fixed bottom-0 left-0 right-0 p-3 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 z-50 md:hidden flex justify-around">
        <NavItem to="/dashboard" icon="🏠" label="" navigate={navigate} currentPath={path} />
        <NavItem to="/analyzer" icon="🔍" label="" navigate={navigate} currentPath={path} />
        <NavItem to="/academy" icon="📚" label="" navigate={navigate} currentPath={path} />
        <NavItem to="/forum" icon="💬" label="" navigate={navigate} currentPath={path} />
        <NavItem to="/settings" icon="⚙️" label="" navigate={navigate} currentPath={path} />
      </div>
    </div>
  );
};


// --- App Initialization ---

const App = () => (
  <ThemeProvider>
    <AuthContext.Provider value={useAuth()}>
      {/* AuthProvider is required to provide the correct context structure */}
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </AuthContext.Provider>
  </ThemeProvider>
);

export default App;
