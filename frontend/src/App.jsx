import React, { useState, useEffect, useRef } from 'react';
import { 
  Plus, 
  Folder, 
  FolderPlus, 
  ChevronDown, 
  ChevronRight, 
  Sun, 
  Moon, 
  Send, 
  Terminal, 
  CheckCircle2, 
  Cpu, 
  Sparkles,
  Archive,
  Trash2
} from 'lucide-react';

const getApiUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  return window.location.origin;
};

const getWsUrl = () => {
  if (import.meta.env.VITE_WS_BASE_URL) return import.meta.env.VITE_WS_BASE_URL;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/chat`;
};

const API_URL = getApiUrl();
const WS_URL = getWsUrl();

export default function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [currentView, setCurrentView] = useState('home'); // home, reports, history
  const [historyList, setHistoryList] = useState([]);
  const [activeTask, setActiveTask] = useState(null);
  
  const [expandedFolders, setExpandedFolders] = useState({
    'CYBERSECURITY WORKFLOWS': false,
    'OCR RESEARCH': false,
    'SYSTEM ARCHITECTURE': true,
    'ARCHIVED TASKS': false,
  });

  const [goalText, setGoalText] = useState('');
  const [inputText, setInputText] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [logs, setLogs] = useState([]);
  const [steps, setSteps] = useState([]);
  const [currentStepId, setCurrentStepId] = useState(null);
  const [taskStatus, setTaskStatus] = useState('Idle');
  const [finalResult, setFinalResult] = useState(null);

  const socketRef = useRef(null);
  const logsEndRef = useRef(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_URL}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (e) {
      console.error("Error fetching history:", e);
    }
  };

  const toggleFolder = (name) => {
    setExpandedFolders(prev => ({ ...prev, [name]: !prev[name] }));
  };

  const handleArchiveTask = async (id, e) => {
    if (e) e.stopPropagation();
    if (!window.confirm("Archive this chat?")) return;
    try {
      const res = await fetch(`${API_URL}/archive/${id}`, { method: 'POST' });
      if (res.ok) {
        fetchHistory();
      }
    } catch (err) {
      console.error("Error archiving task:", err);
    }
  };

  const handleDeleteReport = async (id, e) => {
    if (e) e.stopPropagation();
    if (!window.confirm("Delete this report? This cannot be undone.")) return;
    try {
      const res = await fetch(`${API_URL}/report/${id}`, { method: 'DELETE' });
      if (res.ok) {
        if (activeTask && activeTask.id === id) {
          setActiveTask(null);
          setCurrentView('home');
        }
        fetchHistory();
      }
    } catch (err) {
      console.error("Error deleting report:", err);
    }
  };

  const startTask = (goal) => {
    if (!goal.trim() || isExecuting) return;
    
    setGoalText(goal);
    setIsExecuting(true);
    setLogs([]);
    setSteps([]);
    setCurrentStepId(null);
    setTaskStatus('Planning');
    setFinalResult(null);
    setCurrentView('home');

    if (socketRef.current) {
      socketRef.current.close();
    }

    const ws = new WebSocket(WS_URL);
    socketRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ goal }));
      addLog("sys", "System: Connected to Hermes LangGraph engine. Running reasoning cycle...");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSocketMessage(data);
      } catch (err) {
        console.error("Error parsing WS message:", err);
      }
    };

    ws.onerror = (e) => {
      console.error("WebSocket error:", e);
      addLog("err", "System Error: WebSocket connection error.");
    };

    ws.onclose = () => {
      setIsExecuting(false);
      fetchHistory();
    };
  };

  const handleSocketMessage = (data) => {
    switch (data.type) {
      case 'status':
        setTaskStatus(data.status);
        if (data.summary) {
          addLog("sys", `[Status] ${data.status}: ${data.summary}`);
        }
        if (data.steps) {
          setSteps(data.steps);
        }
        break;
      case 'log':
        const msg = data.message;
        const stepMatch = msg.match(/\[Plan Step (\d+)\]/);
        if (stepMatch) {
          setCurrentStepId(parseInt(stepMatch[1], 10));
        }

        let cat = "info";
        if (msg.includes("[Action]")) cat = "action";
        else if (msg.includes("[LangGraph Node:") || msg.includes("[Reflection System]") || msg.includes("[System]")) cat = "sys";
        else if (msg.includes("[File Writer Result]") || msg.includes("approved")) cat = "success";
        else if (msg.includes("Warning")) cat = "warn";
        else if (msg.includes("[Error]") || msg.includes("Failed")) cat = "err";

        addLog(cat, msg);
        break;
      case 'result':
        const payload = data.payload;
        setFinalResult(payload);
        setTaskStatus('Completed');
        setIsExecuting(false);
        if (payload.steps_executed) {
          setSteps(payload.steps_executed);
        }
        addLog("success", "Task successfully completed!");
        
        setActiveTask({
          id: data.task_id || Date.now(),
          goal: goalText,
          final_report: payload.final_report,
          created_at: new Date().toISOString()
        });
        setCurrentView('reports');
        break;
      case 'error':
        setTaskStatus('Failed');
        setIsExecuting(false);
        addLog("err", data.message);
        break;
      default:
        break;
    }
  };

  const addLog = (category, text) => {
    setLogs(prev => [...prev, { id: Date.now() + Math.random(), category, text }]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    startTask(inputText);
    setInputText('');
  };

  const handleSelectHistoryItem = async (id) => {
    try {
      const res = await fetch(`${API_URL}/report/${id}`);
      if (res.ok) {
        const data = await res.json();
        setActiveTask(data);
        setCurrentView('reports');
      }
    } catch (e) {
      console.error("Error loading report:", e);
    }
  };

  const presetPrompts = [
    "Research next generation AI agent architectures",
    "Analyze Groq LPU inference vs standard GPU performance",
    "Compare Python web frameworks: FastAPI, Flask, and Django",
    "Research vector databases: ChromaDB vs FAISS vs Pinecone"
  ];

  const folderCategories = [
    { name: 'CYBERSECURITY WORKFLOWS', filter: (t) => t.status !== 'Archived' && (t.goal.toLowerCase().includes('cyber') || t.goal.toLowerCase().includes('security')) },
    { name: 'OCR RESEARCH', filter: (t) => t.status !== 'Archived' && (t.goal.toLowerCase().includes('ocr') || t.goal.toLowerCase().includes('vision')) },
    { name: 'SYSTEM ARCHITECTURE', filter: (t) => t.status !== 'Archived' && !t.goal.toLowerCase().includes('cyber') && !t.goal.toLowerCase().includes('ocr') },
    { name: 'ARCHIVED TASKS', filter: (t) => t.status === 'Archived' }
  ];

  const renderMarkdown = (md) => {
    if (!md) return { __html: "" };
    let html = md.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    html = html.replace(/^> (.*?)$/gm, '<blockquote>$1</blockquote>');
    html = html.replace(/^\- (.*?)$/gm, '<li>$1</li>');
    
    html = html.split('\n\n').map(p => {
      const trimmed = p.trim();
      if (trimmed.startsWith('<h') || trimmed.startsWith('<pre') || trimmed.startsWith('<blockquote') || trimmed.startsWith('<li>')) {
        return trimmed;
      }
      return `<p>${trimmed.replace(/\n/g, '<br>')}</p>`;
    }).join('\n');
    
    return { __html: html };
  };

  return (
    <div className={`flex h-screen w-screen overflow-hidden ${darkMode ? 'bg-[#090C15] text-slate-100' : 'bg-slate-50 text-slate-800'}`}>
      
      {/* SIDEBAR */}
      <aside className={`w-72 flex-shrink-0 flex flex-col border-r ${darkMode ? 'bg-[#0E131F] border-slate-800/80' : 'bg-white border-slate-200'}`}>
        <div className="p-4 flex items-center justify-between border-b border-slate-800/60">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
              H
            </div>
            <span className="font-semibold text-lg tracking-tight">Hermes Research</span>
          </div>

          <button 
            onClick={() => setDarkMode(!darkMode)}
            className={`p-2 rounded-lg transition-colors ${darkMode ? 'hover:bg-slate-800 text-slate-400 hover:text-slate-200' : 'hover:bg-slate-100 text-slate-600'}`}
            title="Toggle Theme"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>

        <div className="p-3">
          <button 
            onClick={() => {
              setActiveTask(null);
              setCurrentView('home');
            }}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center gap-2 text-sm"
          >
            <Plus size={16} /> New Research Goal
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
          <div className="px-2 text-[11px] font-bold text-slate-500 tracking-wider uppercase">
            History Folders
          </div>

          <div className="space-y-1">
            {folderCategories.map((cat) => {
              const isExpanded = expandedFolders[cat.name] !== false;
              const matchingItems = historyList.filter(cat.filter);

              return (
                <div key={cat.name} className="space-y-1">
                  <button
                    onClick={() => toggleFolder(cat.name)}
                    className={`w-full flex items-center justify-between p-2 rounded-md text-xs font-semibold tracking-wide uppercase transition-colors ${darkMode ? 'hover:bg-slate-800/60 text-slate-300' : 'hover:bg-slate-100 text-slate-700'}`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <Folder size={15} className="text-indigo-400 shrink-0" />
                      <span className="truncate">{cat.name}</span>
                    </div>
                    <span className="text-[11px] text-slate-500">{matchingItems.length}</span>
                  </button>

                  {isExpanded && (
                    <div className="pl-6 space-y-1 border-l-2 border-slate-800 ml-3">
                      {matchingItems.length === 0 ? (
                        <div className="p-2 text-xs text-slate-500 italic">No items</div>
                      ) : (
                        matchingItems.map((item) => (
                          <div
                            key={item.id}
                            onClick={() => handleSelectHistoryItem(item.id)}
                            className={`group p-2 rounded-md cursor-pointer transition-colors ${darkMode ? 'hover:bg-slate-800/40' : 'hover:bg-slate-100'}`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="text-xs font-medium truncate text-slate-300 group-hover:text-indigo-400">
                                {item.goal}
                              </div>
                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button 
                                  onClick={(e) => handleArchiveTask(item.id, e)} 
                                  className="p-1 hover:text-indigo-400 text-slate-400"
                                  title="Archive Chat"
                                >
                                  <Archive size={12} />
                                </button>
                                <button 
                                  onClick={(e) => handleDeleteReport(item.id, e)} 
                                  className="p-1 hover:text-red-400 text-slate-400"
                                  title="Delete Report"
                                >
                                  <Trash2 size={12} />
                                </button>
                              </div>
                            </div>
                            <div className="flex items-center justify-between mt-1 text-[10px]">
                              <span className="text-emerald-400 font-semibold px-1.5 py-0.5 rounded bg-emerald-950/50 border border-emerald-800/40">
                                {item.status}
                              </span>
                              <span className="text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className={`p-3 border-t text-xs flex items-center justify-between ${darkMode ? 'border-slate-800 text-slate-400' : 'border-slate-200 text-slate-600'}`}>
          <div className="flex items-center gap-2">
            <Cpu size={14} className="text-indigo-400" />
            <span>Groq LPU Engine</span>
          </div>
          <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className={`h-14 border-b px-6 flex items-center justify-between ${darkMode ? 'bg-[#0E131F]/50 border-slate-800' : 'bg-white border-slate-200'}`}>
          <div className="flex gap-2 bg-slate-900/50 p-1 rounded-lg border border-slate-800">
            <button 
              className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${currentView === 'home' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              onClick={() => setCurrentView('home')}
            >
              Workspace Chat
            </button>
            {activeTask && (
              <button 
                className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${currentView === 'reports' ? 'bg-purple-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
                onClick={() => setCurrentView('reports')}
              >
                Report Viewer
              </button>
            )}
            <button 
              className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${currentView === 'history' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              onClick={() => setCurrentView('history')}
            >
              Task Index
            </button>
          </div>
          
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>Groq LPU Backend</span>
          </div>
        </header>

        {currentView === 'home' && (
          <div className="flex-1 grid grid-cols-12 overflow-hidden">
            <section className="col-span-8 flex flex-col justify-between p-8 overflow-y-auto">
              {!goalText ? (
                <div className="max-w-2xl mx-auto w-full space-y-6 my-auto text-center">
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
                    <Sparkles size={14} /> Autonomous Research Suite
                  </div>

                  <h1 className="text-3xl font-bold tracking-tight">
                    Deploy an Autonomous AI Employee
                  </h1>

                  <p className={`text-sm leading-relaxed ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                    Enter research goals, analysis requests, or writing instructions. The Hermes architecture will plan steps, research the web, summarize documents, evaluate outputs, and deliver a comprehensive markdown report.
                  </p>

                  <div className="flex flex-col gap-2.5 pt-4 max-w-xl mx-auto">
                    {presetPrompts.map((prompt, index) => (
                      <button
                        key={index}
                        onClick={() => startTask(prompt)}
                        className={`p-3 text-center text-xs rounded-full border transition-all duration-200 ${
                          darkMode 
                            ? 'bg-slate-900/40 border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 text-slate-200' 
                            : 'bg-white border-slate-200 hover:border-indigo-500 hover:shadow-md text-slate-800'
                        }`}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex-1 space-y-4 overflow-y-auto p-4">
                  <div className="message-bubble user">
                    <div className="avatar">U</div>
                    <div className="message-content"><strong>Goal:</strong> {goalText}</div>
                  </div>
                  <div className="message-bubble">
                    <div className="avatar assistant">H</div>
                    <div className="message-content">
                      {isExecuting ? (
                        <div>
                          <span className="text-indigo-400 font-bold">Hermes is actively processing...</span>
                          <p className="mt-2 text-xs text-slate-400">Current Status: {taskStatus}</p>
                        </div>
                      ) : (
                        <div>
                          <strong className="text-emerald-400">Task Completed!</strong>
                          <p className="mt-1 text-xs text-slate-300">Switch to the Report Viewer tab to read the findings.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div className="max-w-2xl mx-auto w-full pt-6">
                <form onSubmit={handleSubmit} className={`relative flex items-center rounded-xl border shadow-xl ${darkMode ? 'bg-slate-900/80 border-slate-800' : 'bg-white border-slate-200'}`}>
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Enter research task (e.g. Research Groq architecture metrics...)"
                    className="w-full bg-transparent px-4 py-3.5 text-sm outline-none placeholder:text-slate-500"
                    disabled={isExecuting}
                  />
                  <button 
                    type="submit" 
                    disabled={isExecuting || !inputText.trim()}
                    className="mr-2 p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-40"
                  >
                    <Send size={16} />
                  </button>
                </form>
              </div>
            </section>

            <aside className={`col-span-4 border-l flex flex-col relative ${darkMode ? 'bg-[#0A0D14] border-slate-800' : 'bg-slate-100 border-slate-200'}`}>
              <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
                <div className="flex items-center gap-2 font-semibold text-sm">
                  <Terminal size={16} className="text-indigo-400" />
                  <span>Execution Board</span>
                </div>
                {isExecuting && (
                  <span className="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800/50 px-2 py-0.5 rounded font-mono">
                    LIVE LOGS
                  </span>
                )}
              </div>

              <div className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-3">
                <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Console Output</div>
                <div className={`p-3 rounded-lg border min-h-[220px] max-h-[300px] overflow-y-auto ${darkMode ? 'bg-black/60 border-slate-800 text-slate-300' : 'bg-white border-slate-200 text-slate-700'}`}>
                  {logs.length === 0 ? (
                    <span className="text-slate-500">Waiting for action...</span>
                  ) : (
                    logs.map(log => (
                      <div key={log.id} className={`line ${log.category} leading-relaxed`}>
                        {log.text}
                      </div>
                    ))
                  )}
                  <div ref={logsEndRef} />
                </div>
              </div>
            </aside>
          </div>
        )}

        {currentView === 'reports' && activeTask && (
          <div className="flex-1 p-8 overflow-y-auto">
            <div className="max-w-4xl mx-auto bg-slate-900/60 border border-slate-800 rounded-xl p-8 shadow-2xl">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h1 className="text-2xl font-bold mb-2">{activeTask.goal}</h1>
                  <div className="text-xs text-slate-500">{activeTask.created_at}</div>
                </div>
                <div className="flex items-center gap-3">
                  <button 
                    onClick={(e) => handleArchiveTask(activeTask.id, e)}
                    className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1.5"
                  >
                    <Archive size={14} /> Archive Chat
                  </button>
                  <button 
                    onClick={(e) => handleDeleteReport(activeTask.id, e)}
                    className="px-3 py-1.5 text-xs rounded-lg bg-red-950/60 border border-red-800/40 text-red-400 hover:bg-red-900/60 flex items-center gap-1.5"
                  >
                    <Trash2 size={14} /> Delete Report
                  </button>
                </div>
              </div>
              <div 
                className="markdown-body"
                dangerouslySetInnerHTML={renderMarkdown(activeTask.final_report)}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
