const domains = ['Events', 'Teams', 'Projects', 'Judging', 'Results']

export function ScaffoldPage() {
  return (
    <section aria-labelledby="scaffold-title">
      <p className="text-sm font-medium uppercase tracking-widest text-cyan-400">
        DOGFOOD 2026
      </p>
      <h1
        id="scaffold-title"
        className="mt-3 text-4xl font-bold tracking-tight"
      >
        JuryStack is ready for implementation.
      </h1>
      <p className="mt-5 max-w-2xl text-lg text-slate-300">
        The application shell is wired. Product workflows will arrive as tested
        vertical slices.
      </p>
      <ul className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {domains.map((domain) => (
          <li
            className="rounded-lg border border-slate-800 bg-slate-900 p-4"
            key={domain}
          >
            {domain}
          </li>
        ))}
      </ul>
    </section>
  )
}
