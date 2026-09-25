export default function Suggestions({ items, onSelect }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((text) => (
        <button
          key={text}
          onClick={() => onSelect(text)}
          className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs text-blue-700 hover:bg-blue-100"
        >
          {text}
        </button>
      ))}
    </div>
  )
}
