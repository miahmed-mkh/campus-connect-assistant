export default function Message({ message, onFeedback }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[85%] sm:max-w-[70%]">
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'rounded-br-sm bg-blue-600 text-white'
              : message.error
                ? 'rounded-bl-sm border border-red-200 bg-red-50 text-red-700'
                : 'rounded-bl-sm border border-slate-200 bg-white text-slate-800'
          }`}
        >
          {message.text}
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
