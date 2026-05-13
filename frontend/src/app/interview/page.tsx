"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiUrl } from "@/lib/api";

const ROLES = ["AI/ML Engineer", "Backend Engineer", "Data Scientist"];

type Message = {
  sender: "agent" | "user";
  text: string;
  timestamp?: string;
};

type AssessmentMetrics = {
  conceptualUnderstanding: number;
  communicationClarity: number;
  scoreHistory: { conceptual: number; communication: number }[];
};

type ParsedResume = {
  skills?: string[];
  frameworks?: string[];
  technologies?: string[];
  domains?: string[];
  project_technologies?: string[];
};

type RetrievedChunk = {
  text: string;
  metadata?: {
    source?: string;
    role?: string;
  };
  semantic_score?: number;
  skill_overlap?: number;
  role_relevance?: number;
  final_score?: number;
  score?: number;
  reason?: string;
};

type RetrievalEvidence = {
  query?: string;
  chunks?: RetrievedChunk[];
};

type FinalSummary = {
  summary: string;
  verdict: string;
  strong_topics: string[];
  improvement_topics: string[];
  strong_answers: number;
  medium_answers: number;
  weak_answers: number;
};

export default function Interview() {
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [step, setStep] = useState<"upload" | "select-role" | "answer" | "summary">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState("");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);
  const [retrieval, setRetrieval] = useState<RetrievalEvidence>({});
  const [summary, setSummary] = useState<FinalSummary | null>(null);
  const [questionCount, setQuestionCount] = useState(0);
  const [metrics, setMetrics] = useState<AssessmentMetrics>({
    conceptualUnderstanding: 0,
    communicationClarity: 0,
    scoreHistory: [],
  });
  const [candidateName] = useState("Alex Chen");
  const [strengths, setStrengths] = useState<string[]>([]);
  const [weaknesses, setWeaknesses] = useState<string[]>([]);

  useEffect(() => {
    startSession();
  }, []);

  const appendMessage = (message: Message) => {
    setMessages((current) => [...current, message]);
  };

  const streamMessage = async (fullText: string) => {
    // Add an empty agent message first
    const messageId = Date.now();
    setMessages((current) => [...current, { sender: "agent", text: "", timestamp: messageId.toString() }]);

    let displayedText = "";
    const words = fullText.split(" ");
    
    for (const word of words) {
      displayedText += (displayedText ? " " : "") + word;
      setMessages((current) => {
        const last = current[current.length - 1];
        if (last && last.sender === "agent" && last.timestamp === messageId.toString()) {
          return [...current.slice(0, -1), { ...last, text: displayedText }];
        }
        return current;
      });
      // Small delay for "streaming" effect
      await new Promise((resolve) => setTimeout(resolve, 30));
    }
  };

  const formatScore = (score?: number) =>
    typeof score === "number" ? `${Math.round(score * 100)}%` : "n/a";

  const startSession = async () => {
    try {
      const response = await fetch(apiUrl("/api/interview/start"), {
        method: "POST",
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        appendMessage({
          sender: "agent",
          text:
            data?.detail ??
            `Interview API returned ${response.status}. Please make sure the backend is running.`,
        });
        return;
      }

      const data = await response.json();
      setSessionId(data.session_id);
      appendMessage({
        sender: "agent",
        text: "Welcome to DevAssess AI. Please upload your resume to begin the technical screening.",
      });
      setStep("upload");
    } catch (error) {
      console.warn("Failed to start session:", error);
      appendMessage({
        sender: "agent",
        text: "Cannot reach the interview API. Start the backend server and refresh the page.",
      });
    }
  };

  const handleUpload = async () => {
    if (!file || !sessionId) return;
    setLoading(true);

    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("file", file);

    try {
      const response = await fetch(apiUrl("/api/interview/resume"), {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Resume API error: ${response.status}`);
      }
      const data = await response.json();
      setParsedResume(data.parsed_resume);
      appendMessage({ sender: "user", text: `Uploaded: ${file.name}` });
      appendMessage({
        sender: "agent",
        text: "Resume parsed. Review the extracted skills and select your target role.",
      });
      setStep("select-role");
      setFile(null);
    } catch (error) {
      console.error(error);
      appendMessage({
        sender: "agent",
        text: `Upload Error: ${error instanceof Error ? error.message : "Resume parsing failed."}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRoleSelection = async (selectedRole: string) => {
    if (!sessionId) return;
    setLoading(true);
    setRole(selectedRole);
    appendMessage({ sender: "user", text: selectedRole });

    await fetch(apiUrl("/api/interview/role"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, role: selectedRole }),
    });

    await streamMessage("Great! I am preparing your first technical question now.");
    setStep("answer");
    await fetchNextQuestion();
    setLoading(false);
  };

  const fetchNextQuestion = async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(apiUrl("/api/interview/question"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? `Question API error: ${response.status}`);
      }
      setRetrieval(data.retrieval ?? {});
      await streamMessage(data.question);
      setQuestionCount((current) => current + 1);
      setStep("answer");
    } catch (error) {
      console.error(error);
      appendMessage({
        sender: "agent",
        text: `Generation Error: ${error instanceof Error ? error.message : "Unable to generate the next question."}`,
      });
    }
  };

  const submitAnswer = async () => {
    const currentAnswer = answer.trim();
    if (!currentAnswer || !sessionId) return;
    
    setLoading(true);
    setAnswer(""); // Clear textbox immediately
    appendMessage({ sender: "user", text: currentAnswer });

    try {
      const response = await fetch(apiUrl("/api/interview/answer"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, answer: currentAnswer }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? `Answer API error: ${response.status}`);
      }

      await streamMessage(data.feedback);

      if (data.next_question) {
        if (data.next_retrieval) {
          setRetrieval(data.next_retrieval);
        }
        await streamMessage(data.next_question);
        setQuestionCount((current) => current + 1);
      }

      // Calculate scores for this specific answer
      const conceptualScore = data.classification === "strong" ? 95 : data.classification === "medium" ? 75 : 40;
      const wordCount = currentAnswer.split(/\s+/).length;
      const communicationScore = wordCount > 100 ? 95 : wordCount > 40 ? 80 : 60;

      setMetrics((prev) => {
        const newHistory = [...prev.scoreHistory, { conceptual: conceptualScore, communication: communicationScore }];
        const avgConceptual = Math.round(newHistory.reduce((sum, h) => sum + h.conceptual, 0) / newHistory.length);
        const avgCommunication = Math.round(newHistory.reduce((sum, h) => sum + h.communication, 0) / newHistory.length);
        
        return {
          scoreHistory: newHistory,
          conceptualUnderstanding: avgConceptual,
          communicationClarity: avgCommunication,
        };
      });

      // Update strengths and weaknesses
      const topic = data.topic || "Technical Concept";
      if (data.classification === "strong") {
        setStrengths((prev) => Array.from(new Set([...prev, topic])));
      } else if (data.classification === "weak") {
        setWeaknesses((prev) => Array.from(new Set([...prev, topic])));
      }

    } catch (error) {
      console.error(error);
      appendMessage({
        sender: "agent",
        text: `Evaluation Error: ${error instanceof Error ? error.message : "Error evaluating your answer."}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const generateFinalSummary = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const response = await fetch(apiUrl("/api/interview/summary"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail ?? `Summary API error: ${response.status}`);
      }
      setSummary(data);
      setStep("summary");
      appendMessage({ sender: "agent", text: data.summary });
    } catch (error) {
      console.error(error);
      appendMessage({
        sender: "agent",
        text: `Summary Error: ${error instanceof Error ? error.message : "Unable to generate the final summary yet."}`,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex overflow-hidden bg-[#131313]">
      {/* Left Sidebar */}
      <aside className="w-64 bg-[#1c1b1b] border-r border-[#43474c] flex flex-col p-6 gap-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-[#b8c8da] flex items-center justify-center">
            <span className="text-[#0d1d2a] text-lg">⚙️</span>
          </div>
          <div>
            <h3 className="text-[#b8c8da] font-bold text-lg">Interview Context</h3>
            <p className="text-base text-[#8e9196]">Technical Screening Phase</p>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <h3 className="text-sm font-bold text-[#b8c8da] uppercase tracking-widest px-4">Screening Notes</h3>
          
          <div className="px-4 space-y-4">
            <div>
              <p className="text-xs font-bold text-green-500 mb-2">Strengths</p>
              {strengths.length > 0 ? (
                <ul className="text-sm text-[#c4c7cc] list-disc list-inside space-y-1">
                  {strengths.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              ) : (
                <p className="text-xs text-[#8e9196] italic">No strengths identified yet.</p>
              )}
            </div>

            <div>
              <p className="text-xs font-bold text-red-400 mb-2">Weaknesses</p>
              {weaknesses.length > 0 ? (
                <ul className="text-sm text-[#c4c7cc] list-disc list-inside space-y-1">
                  {weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              ) : (
                <p className="text-xs text-[#8e9196] italic">No weaknesses identified yet.</p>
              )}
            </div>
          </div>
        </div>

        <div className="mt-auto pt-6 border-t border-[#43474c]">
          <button className="w-full flex items-center justify-center gap-2 bg-[#474746] text-[#b7b5b4] py-2 rounded-lg hover:brightness-110 transition-all">
            <span className="text-base font-medium">View Scorecard</span>
            <span>↗</span>
          </button>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col bg-[#131313]">
        {/* Header */}
        <header className="px-8 py-4 border-b border-[#43474c] flex justify-between items-center bg-[#131313]/50 backdrop-blur-md">
          <div>
            <h2 className="text-[#e5e2e1] font-bold text-2xl">{role || "Select a Role"}</h2>
            <p className="text-base text-[#8e9196] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#b8c8da]"></span>
              {questionCount ? `Question ${questionCount} in progress` : "Assessment in progress..."}
            </p>
          </div>
          <div className="flex gap-2">
            {role && (
              <>
                <span className="text-base px-2 py-1 bg-[#2a2a2a] rounded border border-[#43474c] text-[#c4c7cc]">
                  Senior Level
                </span>
                <span className="text-base px-2 py-1 bg-[#2a2a2a] rounded border border-[#43474c] text-[#c4c7cc]">
                  {role.split(" ")[0]}
                </span>
              </>
            )}
          </div>
        </header>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6 flex flex-col">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.sender === "agent" ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`flex gap-3 max-w-[70%] ${
                  msg.sender === "agent" ? "flex-row" : "flex-row-reverse"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded flex-shrink-0 flex items-center justify-center text-base ${
                    msg.sender === "agent"
                      ? "bg-[#b8c8da] text-[#0d1d2a]"
                      : "bg-[#c8c6c5] text-[#1b1b1c]"
                  }`}
                >
                  {msg.sender === "agent" ? "🤖" : "👤"}
                </div>
                <div
                  className={`p-4 rounded-xl ${
                    msg.sender === "agent"
                      ? "bg-[#1c1b1b] border-l-4 border-[#b8c8da] shadow-lg"
                      : "bg-[#2a2a2a] border border-[#43474c]"
                  }`}
                >
                  <p className="text-[#e5e2e1] text-lg leading-relaxed">{msg.text}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="px-8 py-6 bg-[#0e0e0e] border-t border-[#43474c]">
          <div className="max-w-4xl mx-auto flex items-end gap-4">
            {step === "upload" ? (
              <div className="flex-1 flex gap-3">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="flex-1 px-4 py-2 bg-[#1c1b1b] border border-[#43474c] rounded-lg text-[#e5e2e1] text-lg file:hidden"
                />
                <Button
                  onClick={handleUpload}
                  disabled={!file || loading}
                  className={`px-6 py-2 text-lg font-bold rounded-lg transition-all ${
                    loading
                      ? "bg-[#b8c8da]/80 text-[#0d1d2a] cursor-wait"
                      : "bg-[#b8c8da] text-[#0d1d2a] hover:brightness-110"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {loading && <span className="inline-block animate-spin">⏳</span>}
                    {loading ? "Parsing PDF..." : "Upload"}
                  </span>
                </Button>
              </div>
            ) : step === "select-role" ? (
              <div className="flex-1 grid gap-4">
                {parsedResume && (
                  <div className="grid grid-cols-2 gap-3 text-base text-[#c4c7cc]">
                    <div className="bg-[#1c1b1b] border border-[#43474c] rounded-lg p-3">
                      <p className="mb-2 font-bold text-[#b8c8da]">Skills</p>
                      <p>{(parsedResume.skills ?? []).join(", ") || "No skills detected"}</p>
                    </div>
                    <div className="bg-[#1c1b1b] border border-[#43474c] rounded-lg p-3">
                      <p className="mb-2 font-bold text-[#b8c8da]">Domains</p>
                      <p>{(parsedResume.domains ?? []).join(", ") || "No domains detected"}</p>
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-3">
                  {ROLES.map((r) => (
                    <Button
                      key={r}
                      onClick={() => handleRoleSelection(r)}
                      disabled={loading}
                      className="bg-[#2a2a2a] text-[#e5e2e1] hover:bg-[#43474c] border border-[#43474c] py-2 text-lg rounded-lg transition-all"
                    >
                      {r}
                    </Button>
                  ))}
                </div>
              </div>
            ) : step === "summary" && summary ? (
              <div className="flex-1 bg-[#1c1b1b] border border-[#43474c] rounded-xl p-4 text-lg text-[#e5e2e1]">
                <p className="font-bold text-[#b8c8da] mb-2">{summary.verdict}</p>
                <p>{summary.summary}</p>
              </div>
            ) : (
              <div className="flex-1 bg-[#1c1b1b] border border-[#43474c] rounded-xl flex flex-col p-2 focus-within:border-[#b8c8da] transition-all">
                <Textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Type your technical response here..."
                  className="w-full bg-transparent border-none focus:ring-0 text-[#e5e2e1] text-lg resize-none px-4 py-3 placeholder-[#8e9196]/50"
                  rows={2}
                />
                <div className="flex items-center justify-between px-3 py-2 border-t border-[#43474c]/30 mt-2">
                  <div className="flex gap-2">
                  </div>
                  <Button
                    onClick={submitAnswer}
                    disabled={!answer.trim() || loading}
                    className="bg-[#b8c8da] text-[#0d1d2a] hover:brightness-110 px-4 py-1 text-base font-bold rounded-lg transition-all"
                  >
                    {loading ? "Submitting..." : "SEND →"}
                  </Button>
                  <Button
                    onClick={generateFinalSummary}
                    disabled={loading || questionCount === 0}
                    className="bg-[#2a2a2a] text-[#e5e2e1] hover:bg-[#43474c] px-4 py-1 text-base font-bold rounded-lg border border-[#43474c]"
                  >
                    Final Summary
                  </Button>
                </div>
              </div>
            )}
          </div>
          <p className="text-center text-sm text-[#8e9196]/40 mt-3 uppercase tracking-widest">
            Encrypted Session • Real-time AI Assessment
          </p>
        </div>
      </main>

      {/* Right Sidebar - Metrics */}
      <aside className="hidden xl:flex flex-col w-80 bg-[#1c1b1b] border-l border-[#43474c] p-6 gap-6">
        <div className="space-y-2">
          <h3 className="text-base text-[#8e9196] uppercase tracking-widest font-bold">
            Live Assessment Profile
          </h3>

          <div className="bg-[#131313] p-4 rounded-xl border border-[#43474c] space-y-4">
            <div>
              <div className="flex justify-between items-end mb-2">
                <span className="text-base text-[#8e9196]">Conceptual Understanding</span>
                <span className="text-2xl text-[#b8c8da] font-bold">{metrics.conceptualUnderstanding}%</span>
              </div>
              <div className="w-full h-1 bg-[#2a2a2a] rounded-full overflow-hidden">
                <div
                  className="bg-[#b8c8da] h-full transition-all"
                  style={{ width: `${metrics.conceptualUnderstanding}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-end mb-2">
                <span className="text-base text-[#8e9196]">Communication Clarity</span>
                <span className="text-2xl text-[#b8c8da] font-bold">{metrics.communicationClarity}%</span>
              </div>
              <div className="w-full h-1 bg-[#2a2a2a] rounded-full overflow-hidden">
                <div
                  className="bg-[#b8c8da] h-full transition-all"
                  style={{ width: `${metrics.communicationClarity}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-2 min-h-0">
          <h3 className="text-base text-[#8e9196] uppercase tracking-widest font-bold">
            RAG Evidence
          </h3>
          <div className="bg-[#131313] border border-[#43474c] rounded-xl p-4 space-y-3 max-h-[420px] overflow-y-auto">
            <div>
              <p className="text-sm uppercase tracking-widest text-[#8e9196] mb-1">
                Generated Query
              </p>
              <p className="text-base text-[#c4c7cc]">
                {retrieval.query || "No retrieval query yet."}
              </p>
            </div>
            {(retrieval.chunks ?? []).map((chunk, idx) => (
              <div
                key={`${chunk.metadata?.source ?? "chunk"}-${idx}`}
                className="border-t border-[#43474c]/50 pt-3 text-base text-[#c4c7cc] space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-[#b8c8da] truncate">
                    {chunk.metadata?.source ?? "Retrieved chunk"}
                  </span>
                  <span className="text-[#e5e2e1]">{formatScore(chunk.final_score ?? chunk.score)}</span>
                </div>
                <p className="text-[#8e9196]">
                  semantic {formatScore(chunk.semantic_score)} / skills {formatScore(chunk.skill_overlap)} / role{" "}
                  {formatScore(chunk.role_relevance)}
                </p>
                <p>{chunk.reason}</p>
                <p className="line-clamp-4">{chunk.text}</p>
              </div>
            ))}
          </div>
        </div>

      </aside>
    </div>
  );
}
