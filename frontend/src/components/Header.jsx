export default function Header({ onReset }) {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 font-bold text-white">
          CC
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-800">Campus Connect</h1>
          <p className="text-xs text-slate-500">Assistant virtuel de l’ESIC</p>
        </div>
      </div>

      <button
        onClick={onReset}
        className="whitespace-nowrap rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
      >
        ↻ Recommencer
      </button>
    </header>
  )
}
