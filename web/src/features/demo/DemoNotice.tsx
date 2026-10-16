import { Link } from 'react-router-dom'
export function DemoNotice({
  title,
  guide,
  children,
}: {
  title: string
  guide: string
  children: string
}) {
  return (
    <section className="settings-card demo-notice">
      <h2>{title}</h2>
      <p>{children}</p>
      <Link to={`/guide/${guide}`}>查看功能说明 →</Link>
    </section>
  )
}
