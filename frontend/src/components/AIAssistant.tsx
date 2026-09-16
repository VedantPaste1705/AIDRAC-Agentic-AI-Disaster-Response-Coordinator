import { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import {
  Send, Bot, Shield, MapPin, ChevronDown, ChevronUp, Check, AlertTriangle,
  Hospital, Home, Building2, Flame, Pill, Loader2, MessageSquare,
} from 'lucide-react';
import { aiApi } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import type { AIRecommendationResponse, AIMessage } from '../types';
import { getOrCreateIncidentId } from '../utils/incident';
import Button from './ui/Button';
import Badge from './ui/Badge';
import LoadingSpinner from './ui/LoadingSpinner';

const RISK_VARIANTS: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  safe: 'default',
  low: 'info',
  moderate: 'warning',
  high: 'danger',
  extreme: 'danger',
};

const RISK_LABELS: Record<string, string> = {
  safe: 'Safe',
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  extreme: 'Extreme',
};

const DEST_ICONS: Record<string, React.ReactNode> = {
  hospital:        <Hospital className="h-6 w-6" />,
  shelter:         <Home className="h-6 w-6" />,
  school:          <Building2 className="h-6 w-6" />,
  community_centre: <Building2 className="h-6 w-6" />,
  police:          <Shield className="h-6 w-6" />,
  firestation:     <Flame className="h-6 w-6" />,
  fire_station:    <Flame className="h-6 w-6" />,
  pharmacy:        <Pill className="h-6 w-6" />,
};

const DEST_LABELS: Record<string, string> = {
  hospital:         'Hospital',
  shelter:          'Shelter',
  school:           'School',
  community_centre: 'Community Centre',
  police:           'Police Station',
  firestation:      'Fire Station',
  fire_station:     'Fire Station',
  pharmacy:         'Pharmacy',
};

interface AIAssistantProps {
  initialQuestion?: string;
  className?: string;
}

interface AIAssistantRef {
  submitQuestion: (question: string) => void;
}

export default function AIAssistant(
  { initialQuestion, className = '' }: AIAssistantProps,
  ref: React.Ref<AIAssistantRef>
) {
  const { position } = useGeolocation({ watch: false });
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [globalLoading, setGlobalLoading] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);
  const submittedRef = useRef<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const incidentId = getOrCreateIncidentId();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (initialQuestion && initialQuestion !== submittedRef.current) {
      setQuestion(initialQuestion);
      submittedRef.current = initialQuestion;
    }
  }, [initialQuestion]);

  useEffect(() => {
    if (question && question === submittedRef.current && submittedRef.current && !globalLoading) {
      handleSubmit();
    }
  }, [question, globalLoading]);

  const submitQuestion = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || globalLoading) return;

    setGlobalLoading(true);

    const userMessage: AIMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
      timestamp: Date.now(),
    };

    const assistantMessage: AIMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      loading: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setQuestion('');
    submittedRef.current = '';

    try {
      const body = { question: trimmed, lat: position?.lat, lng: position?.lng, incident_id: incidentId };
      const resp = await aiApi.recommend(body);
      const response = resp.data;

      setMessages((prev) => prev.map((msg) =>
        msg.id === assistantMessage.id
          ? { ...msg, content: response.summary, response, loading: false }
          : msg
      ));
    } catch (e: any) {
      const errorMsg = e?.response?.data?.detail || e?.message || 'Failed to get recommendation';
      setMessages((prev) => prev.map((msg) =>
        msg.id === assistantMessage.id
          ? { ...msg, content: errorMsg, error: errorMsg, loading: false }
          : msg
      ));
    } finally {
      setGlobalLoading(false);
    }
  };

  useImperativeHandle(ref, () => ({
    submitQuestion,
  }));

  const handleSubmit = () => {
    submitQuestion(question);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const retryMessage = (messageId: string) => {
    const msg = messages.find((m) => m.id === messageId);
    if (msg && msg.role === 'user' && !globalLoading) {
      submitQuestion(msg.content);
    }
  };

  const renderMessage = (msg: AIMessage) => {
    const isUser = msg.role === 'user';
    const isLoading = msg.loading;
    const hasError = !!msg.error;

    return (
      <div
        key={msg.id}
        className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-fade-in`}
      >
        {!isUser && (
          <div className="shrink-0 w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 flex-shrink-0">
            <Bot className="h-5 w-5" />
          </div>
        )}
        <div className={`flex-1 min-w-0 ${isUser ? 'text-right' : ''}`}>
          <div className={`inline-block max-w-[85%] px-4 py-3 rounded-2xl ${isUser
            ? 'bg-primary-500/20 border border-primary-500/30 text-white'
            : hasError
              ? 'bg-danger-500/15 border border-danger-500/30 text-danger-300'
              : 'bg-stitch-surface border border-stitch-border text-on-surface'
          }`}>
            {isLoading && !isUser && (
              <div className="flex items-center gap-2 text-sm text-on-surface-variant">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Analyzing...</span>
              </div>
            )}
            {!isLoading && (
              <>
                <p className="text-base leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                {msg.response && (
                  <div className="mt-3 space-y-3">
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-primary-500/10 border border-primary-500/20">
                      <Shield className="h-5 w-5 text-primary-400 shrink-0" />
                      <div>
                        <p className="text-xs text-on-surface-variant uppercase tracking-wider">Risk Level</p>
                        <Badge
                          variant={RISK_VARIANTS[(msg.response.riskLevel ?? '').toLowerCase()] || 'default'}
                          size="sm"
                          className="mt-0.5"
                        >
                          {RISK_LABELS[(msg.response.riskLevel ?? '').toLowerCase()] || 'Unknown'}
                        </Badge>
                      </div>
                    </div>

                    {msg.response.recommendedDestination && (
                      <div className="flex items-center gap-3 p-3 rounded-xl bg-primary-500/10 border border-primary-500/20">
                        <div className="shrink-0 w-10 h-10 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400">
                          {DEST_ICONS[msg.response.recommendedDestination.type.toLowerCase()] || <MapPin className="h-5 w-5" />}
                        </div>
                        <div>
                          <p className="text-xs text-primary-400 uppercase tracking-wider font-medium">
                            {DEST_LABELS[msg.response.recommendedDestination.type.toLowerCase()] || msg.response.recommendedDestination.type}
                          </p>
                          <p className="text-sm font-semibold text-on-surface">{msg.response.recommendedDestination.name}</p>
                        </div>
                      </div>
                    )}

                    {msg.response.reason && (
                      <div className="p-3 rounded-xl bg-stitch-surface border border-stitch-border">
                        <p className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Reason</p>
                        <p className="text-sm text-on-surface leading-relaxed">{msg.response.reason}</p>
                      </div>
                    )}

                    {msg.response.actions.length > 0 && (
                      <div className="p-3 rounded-xl bg-stitch-surface border border-stitch-border">
                        <p className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-2">Recommended Actions</p>
                        <ul className="space-y-2">
                          {msg.response.actions.map((action, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-on-surface">
                              <span className="shrink-0 w-5 h-5 rounded-full bg-success-500/20 flex items-center justify-center mt-0.5">
                                <Check className="h-3.5 w-3.5 text-success-400" />
                              </span>
                              <span>{action}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {hasError && (
                  <div className="mt-3 flex gap-2">
                    <Button variant="primary" size="sm" onClick={() => retryMessage(msg.id)} icon={<Loader2 className="h-3.5 w-3.5" />}>
                      Retry
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
          <p className={`text-xs text-on-surface-variant/60 mt-1 ${isUser ? 'text-right' : ''}`}>
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
        {isUser && (
          <div className="shrink-0 w-8 h-8 rounded-full bg-slate-700/50 flex items-center justify-center text-slate-300 flex-shrink-0">
            <MessageSquare className="h-5 w-5" />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-5 text-sm text-on-surface-variant">
        <MapPin className="h-4 w-4" />
        {position
          ? <>Current Location: {position.lat.toFixed(4)}, {position.lng.toFixed(4)}</>
          : <span className="text-on-surface-variant/60">Location unavailable</span>
        }
        <span className="ml-auto text-xs font-mono text-slate-600">Incident: {incidentId.slice(0, 8)}</span>
      </div>

      <div className="flex gap-3 mb-5">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about evacuations, safe routes, resource allocation..."
          disabled={globalLoading}
          className="w-full px-5 py-3.5 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl text-base text-on-surface placeholder:text-slate-400 transition-all duration-200 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:bg-slate-800/80 disabled:opacity-50 disabled:bg-slate-900"
        />
        <Button size="lg" onClick={handleSubmit} loading={globalLoading} disabled={!question.trim() || globalLoading} icon={<Send className="h-5 w-5" />}>
          Analyze
        </Button>
      </div>

      <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1" role="log" aria-live="polite">
        {messages.length === 0 && !globalLoading && (
          <div className="flex flex-col items-center py-8 text-center">
            <Bot className="h-12 w-12 text-on-surface-variant/20 mb-4" />
            <p className="text-base font-medium text-on-surface-variant">Ask anything about your safety.</p>
            <p className="text-sm text-on-surface-variant/60 mt-1">Quick actions or type your question below.</p>
          </div>
        )}
        {messages.map(renderMessage)}
        <div ref={messagesEndRef} />
      </div>

      {messages.length > 0 && (
        <div className="pt-3 border-t border-stitch-border">
          <p className="text-sm font-medium text-on-surface-variant uppercase tracking-wider mb-2">Powered by</p>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-on-surface-variant">
            <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-success-500" /> OpenWeather</span>
            <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-success-500" /> IMD / NDMA CAP Alerts</span>
            <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-success-500" /> OpenStreetMap</span>
            <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-success-500" /> Gemini</span>
          </div>
        </div>
      )}
    </div>
  );
}

export const AIAssistantWithRef = forwardRef(AIAssistant);
AIAssistantWithRef.displayName = 'AIAssistant';