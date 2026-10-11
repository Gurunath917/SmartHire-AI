import { useState, useEffect, useRef } from 'react';
import { assistantAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader } from '../../components/ui';
import { Send, Bot, User, BookOpen } from 'lucide-react';
import toast from 'react-hot-toast';

const SUGGESTED = [
  'What skills do I need for an AI/ML Engineer role?',
  'How can I improve my resume?',
  'What ML topics should I prepare for interviews?',
  'How do I transition into a data science career?',
];

export default function CandidateAssistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (text) => {
    if (!text.trim() || loading) return;
    const question = text.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'USER', content: question }]);
    setLoading(true);

    try {
      const r = await assistantAPI.chat(question, sessionId);
      setSessionId(r.data.session_id);
      setMessages(prev => [...prev, {
        role: 'ASSISTANT',
        content: r.data.assistant_answer,
        sources: r.data.sources,
      }]);
    } catch {
      toast.error('Assistant unavailable. Try again.');
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="AI Career Assistant"
        subtitle="Ask anything about skills, interviews, resume, or career paths."
      />

      <div className="flex flex-col h-[calc(100vh-200px)] card p-0 overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Bot size={40} className="text-primary-400 mb-3" />
              <p className="font-medium text-gray-700">Ask me anything about your career</p>
              <p className="text-sm text-gray-500 mb-6">Powered by RAG — answers grounded in real documents</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {SUGGESTED.map(q => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="text-left text-sm p-3 border border-gray-200 rounded-lg hover:bg-primary-50 hover:border-primary-300 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'USER' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    msg.role === 'USER' ? 'bg-primary-600' : 'bg-gray-200'
                  }`}>
                    {msg.role === 'USER'
                      ? <User size={14} className="text-white" />
                      : <Bot size={14} className="text-gray-600" />
                    }
                  </div>
                  <div className={`max-w-[80%] ${msg.role === 'USER' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                    <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'USER'
                        ? 'bg-primary-600 text-white rounded-tr-sm'
                        : 'bg-gray-100 text-gray-800 rounded-tl-sm'
                    }`}>
                      {msg.content}
                    </div>
                    {msg.sources?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {msg.sources.map((s, si) => (
                          <span key={si} className="flex items-center gap-1 text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                            <BookOpen size={10} /> {s.title}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <Bot size={14} className="text-gray-600" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex gap-1 items-center">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={e => { e.preventDefault(); send(input); }} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about skills, career paths, interview prep..."
              className="input flex-1"
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()} className="btn-primary px-4">
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </DashboardLayout>
  );
}
