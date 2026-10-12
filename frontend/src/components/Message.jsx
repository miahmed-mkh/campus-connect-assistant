import ReactMarkdown from 'react-markdown'
import remarkBreaks from 'remark-breaks'

// Rendu des réponses Markdown de l'API (titres, gras, listes).
// react-markdown échappe le HTML brut : aucun risque d'injection.
const markdownComponents = {
  h1: ({ children }) => <h3 className="mb-1 mt-2 text-base font-semibold first:mt-0">{children}</h3>,
  h2: ({ children }) => <h3 className="mb-1 mt-2 text-base font-semibold first:mt-0">{children}</h3>,
  h3: ({ children }) => <h4 className="mb-1 mt-2 text-sm font-semibold first:mt-0">{children}</h4>,
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="mb-2 list-disc space-y-0.5 pl-5 last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 list-decimal space-y-0.5 pl-5 last:mb-0">{children}</ol>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="underline">
      {children}
    </a>
  ),
  code: ({ children }) => <code className="rounded bg-slate-100 px-1 text-xs">{children}</code>,
}

export default function Message({ message, onFeedback }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[85%] sm:max-w-[70%]">
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'rounded-br-sm bg-blue-600 text-white whitespace-pre-wrap'
              : message.error
                ? 'rounded-bl-sm border border-red-200 bg-red-50 text-red-700'
                : 'rounded-bl-sm border border-slate-200 bg-white text-slate-800'
          }`}
        >
          {isUser ? (
            message.text
          ) : (
            <ReactMarkdown remarkPlugins={[remarkBreaks]} components={markdownComponents}>
              {message.text}
            </ReactMarkdown>
          )}
        </div>

        {!isUser && message.source && (
          <p className="mt-1 pl-1 text-xs text-slate-500">Source : {message.source}</p>
        )}

        {!isUser && !message.error && message.id !== 'welcome' && (
          <div className="mt-1 flex gap-1 pl-1">
            <button
              onClick={() => onFeedback(message.id, 'up')}
              disabled={message.feedback}
              className={`rounded px-1.5 text-sm ${
                message.feedback === 'up' ? 'bg-green-100' : 'opacity-60 hover:opacity-100'
              }`}
              title="Réponse utile"
            >
              👍
            </button>
            <button
              onClick={() => onFeedback(message.id, 'down')}
              disabled={message.feedback}
              className={`rounded px-1.5 text-sm ${
                message.feedback === 'down' ? 'bg-red-100' : 'opacity-60 hover:opacity-100'
              }`}
              title="Réponse pas utile"
            >
              👎
            </button>
          </div>
        )}

        <p className={`mt-0.5 text-[10px] text-slate-400 ${isUser ? 'text-right pr-1' : 'pl-1'}`}>
          {message.time}
        </p>
      </div>
    </div>
  )
}
