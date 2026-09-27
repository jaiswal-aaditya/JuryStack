import { Link } from 'react-router'

export function Brand({
  linked = true,
  large = false,
}: {
  linked?: boolean
  large?: boolean
}) {
  const content = (
    <span className={`brand ${large ? 'brand-large' : ''}`}>
      <img alt="" className="brand-logo" src="/logo.png" />
      <span className="brand-wordmark">
        <span>Jury</span>
        <span className="brand-accent">Stack</span>
      </span>
    </span>
  )
  return linked ? (
    <Link aria-label="JuryStack home" to="/">
      {content}
    </Link>
  ) : (
    content
  )
}
