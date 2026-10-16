export function DemoNotice({ title, children }: { title: string; children: string }) {
  return (
    <section className="settings-card demo-notice">
      <h2>{title}</h2>
      <p>{children}</p>
    </section>
  )
}
