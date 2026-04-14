import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Bot, Mail, Lock, ArrowRight, Sparkles, Shield, CheckCircle2 } from 'lucide-react';

interface LoginPageProps {
  onLogin: (email: string) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState('demo@smartcopilot.com');
  const [password, setPassword] = useState('demo123');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    // Simulate local authentication
    setTimeout(() => {
      if (email && password) {
        onLogin(email);
      } else {
        setError('Please enter both email and password.');
        setIsLoading(false);
      }
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex overflow-hidden font-sans">
      {/* Left Side - Branding & Features */}
      <div className="hidden lg:flex lg:w-1/2 relative flex-col justify-between p-12 overflow-hidden border-r border-white/5">
        {/* Background Atmosphere */}
        <div className="absolute inset-0 z-0">
          <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-secondary/20 rounded-full blur-[120px] animate-pulse" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 bg-secondary rounded-xl flex items-center justify-center shadow-lg shadow-secondary/20">
              <Bot size={24} className="text-on-secondary" />
            </div>
            <span className="text-xl font-bold tracking-tight font-headline">Smart Copilot</span>
          </div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="max-w-md"
          >
            <h1 className="text-6xl font-bold leading-[1.1] mb-8 font-headline tracking-tight">
              Your Intelligence, <span className="text-secondary">Amplified.</span>
            </h1>
            <p className="text-lg text-white/60 leading-relaxed mb-12">
              The modern workspace for editorial research, content curation, and deep-dive analysis. Powered by advanced AI to help you think better.
            </p>

            <div className="space-y-6">
              {[
                { icon: <Sparkles className="text-secondary" />, title: "AI-Powered Curation", desc: "Intelligent content discovery and analysis." },
                { icon: <Shield className="text-blue-400" />, title: "Secure Workspace", desc: "Enterprise-grade security for your research." },
                { icon: <CheckCircle2 className="text-green-400" />, title: "Editorial Precision", desc: "Tools designed for professional writers." }
              ].map((feature, i) => (
                <motion.div 
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + (i * 0.1) }}
                  className="flex gap-4 items-start"
                >
                  <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                    {feature.icon}
                  </div>
                  <div>
                    <h3 className="font-bold text-sm mb-1">{feature.title}</h3>
                    <p className="text-xs text-white/40">{feature.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        <div className="relative z-10 flex items-center gap-6 text-xs text-white/40 font-medium">
          <span>© 2026 Smart Copilot Inc.</span>
          <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
          <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 bg-white text-black relative">
        <div className="absolute top-8 right-8 lg:hidden">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-secondary rounded-lg flex items-center justify-center">
              <Bot size={18} className="text-on-secondary" />
            </div>
            <span className="font-bold tracking-tight">Smart Copilot</span>
          </div>
        </div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md"
        >
          <div className="mb-10">
            <h2 className="text-3xl font-bold font-headline mb-2">Welcome back</h2>
            <p className="text-black/50 text-sm">Please enter your details to sign in.</p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl flex items-center gap-3">
              <Shield size={18} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-black/40 ml-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-black/30" size={18} />
                <input 
                  type="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full pl-12 pr-4 py-3.5 bg-black/5 border-none rounded-xl text-sm focus:ring-2 focus:ring-secondary/20 transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center ml-1">
                <label className="text-xs font-bold uppercase tracking-wider text-black/40">Password</label>
                <a href="#" className="text-xs font-bold text-secondary hover:underline">Forgot?</a>
              </div>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-black/30" size={18} />
                <input 
                  type="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-12 pr-4 py-3.5 bg-black/5 border-none rounded-xl text-sm focus:ring-2 focus:ring-secondary/20 transition-all"
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={isLoading}
              className="w-full bg-black text-white py-4 rounded-xl font-bold text-sm hover:bg-black/90 transition-all flex items-center justify-center gap-2 group disabled:opacity-70"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign In
                  <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
