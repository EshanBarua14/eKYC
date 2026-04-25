import Spinner from "./Spinner"
import EmptyState from "./EmptyState"
import { FileText } from "lucide-react"

export default function Table({ columns, data, loading, emptyTitle = "No records", emptyDesc = "", onRowClick }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 dark:bg-gray-800/50">
            {columns.map((col, i) => (
              <th key={i} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
          {loading ? (
            <tr><td colSpan={columns.length} className="py-12 text-center"><Spinner/></td></tr>
          ) : data.length === 0 ? (
            <tr><td colSpan={columns.length}>
              <EmptyState icon={<FileText size={24}/>} title={emptyTitle} desc={emptyDesc}/>
            </td></tr>
          ) : data.map((row, ri) => (
            <tr key={ri}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`bg-white dark:bg-gray-900 transition-colors ${onRowClick ? "cursor-pointer hover:bg-brand-50 dark:hover:bg-brand-950/20" : ""}`}
            >
              {columns.map((col, ci) => (
                <td key={ci} className="px-4 py-3 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                  {col.render ? col.render(row[col.key], row) : row[col.key] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
