function initials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

export function Avatar({
  name,
  size = 'md',
  role,
}: {
  name: string
  size?: 'sm' | 'md' | 'lg'
  role?: string
}) {
  return (
    <span
      aria-hidden="true"
      className={`avatar avatar-${size}${role ? ` avatar-role-${role}` : ''}`}
    >
      {initials(name) || '?'}
    </span>
  )
}
