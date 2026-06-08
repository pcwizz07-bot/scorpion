import { createFileRoute } from '@tanstack/react-router'
import { useSuspenseQuery } from '@tanstack/react-query'
import { convexQuery } from '@convex-dev/react-query'
import { useMutation } from 'convex/react'
import { api } from '../../convex/_generated/api'
import { useState } from 'react'

export const Route = createFileRoute('/ai-investigator')({
  head: () => ({ meta: [{ title: 'AI Investigator - IMSI Catcher' }] }),
  component: AiInvestigatorPage,
})

function AiInvestigatorPage() {
  const [threadId, setThreadId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([])
  const [loading, setLoading] = useState(false)
  const createThread = useMutation(api.chat.createThread)
  const sendMessage = useMutation(api.chat.sendMessage)

  const handleStart = async () => {
    const { threadId: tid } = await createThread()
    setThreadId(tid)
    setMessages([
      {
        role: 'assistant',
        content: `# IMSI Intelligence Analyst Online

I am connected to the surveillance network. I can:
- **Analyze IMSI patterns** across all 3 Pi devices
- **Triangulate positions** of detected phones
- **Identify suspicious activity** on the reserve
- **Generate intelligence reports** for ranger deployment

What would you like me to investigate?`,
      },
    ])
  }

  const handleSend = async () => {
    if (!input.trim() || !threadId) return
    const prompt = input
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: prompt }])
    setLoading(true)

    try {
      await sendMessage({ threadId, prompt })
      // Poll for response - in production use streaming
      const checkMessages = async () => {
        // Simple approach: just add a placeholder and simulate
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `Analyzing: "${prompt.slice(0, 50)}..."\n\nRunning intelligence analysis... Check the investigator dashboard for real-time streaming results.`,
          },
        ])
        setLoading(false)
      }
      setTimeout(checkMessages, 1000)
    } catch (err) {
      setLoading(false)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error: Failed to get response. Ensure OPENROUTER_API_KEY is configured.' },
      ])
    }
  }

  const quickPrompts = [
    'What IMSIs are currently active on the reserve?',
    'Analyze movement patterns in the last 24 hours',
    'Generate a threat assessment report',
    'Are there any new IMSIs that appeared today?',
    'Which areas have the most cellular activity?',
    'Correlate sightings across all 3 Pi devices',
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <a href="/" className="flex items-center gap-2 text-gray-400 hover:text-white">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Dashboard
            </a>
            <div className="h-6 w-px bg-gray-700" />
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 text-sm font-bold">
              AI
            </div>
            <h1 className="text-lg font-bold">AI Intelligence Analyst</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-purple-400" />
            <span className="text-sm text-gray-400">Powered by OpenRouter</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-6">
        {!threadId ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="mb-8 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-blue-600">
              <svg className="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h2 className="mb-2 text-2xl font-bold">IMSI Intelligence Analyst</h2>
            <p className="mb-8 text-center text-gray-400">
              Connect to the AI investigator to analyze IMSI data, <br />
              detect patterns, and generate actionable intelligence.
            </p>
            <button
              onClick={handleStart}
              className="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-3 font-medium text-white shadow-lg shadow-purple-600/30 transition-all hover:from-purple-500 hover:to-blue-500"
            >
              Start Investigation Session
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-6">
            {/* Quick prompts sidebar */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-400">Quick Analysis</h3>
              {quickPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(prompt)
                    if (!loading) {
                      setInput(prompt)
                    }
                  }}
                  className="w-full rounded-lg border border-gray-700 px-3 py-2 text-left text-xs text-gray-300 transition-colors hover:border-purple-500 hover:bg-purple-900/20"
                >
                  {prompt}
                </button>
              ))}
            </div>

            {/* Chat area */}
            <div className="col-span-3 flex flex-col gap-4">
              <div className="flex-1 space-y-4 rounded-xl border border-gray-700 bg-gray-800/30 p-4">
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-800 text-gray-200'
                      }`}
                    >
                      <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-purple-400" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-purple-400" style={{ animationDelay: '0.1s' }} />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-purple-400" style={{ animationDelay: '0.2s' }} />
                    </div>
                    Analyzing intelligence data...
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask the AI investigator..."
                  className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                />
                <button
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  className="rounded-lg bg-purple-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-purple-500 disabled:opacity-50"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}