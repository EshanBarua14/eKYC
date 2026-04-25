export default function Footer() {
  return (
    <footer className="mt-auto py-4 px-6 border-t border-gray-100 dark:border-gray-800
                       bg-white dark:bg-gray-950">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-gray-400">
        <p>Design &amp; Developed by <span className="font-semibold text-brand-600">Xpert Fintech Ltd.</span></p>
        <p>BFIU Circular No. 29 Compliant · Bangladesh Financial Intelligence Unit</p>
        <p>© {new Date().getFullYear()} All rights reserved</p>
      </div>
    </footer>
  )
}
