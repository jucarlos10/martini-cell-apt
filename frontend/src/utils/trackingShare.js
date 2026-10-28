export function buildTrackingShare(trackingCode, origin) {
  const code = String(trackingCode || '').trim()
  const consultationUrl = new URL('/consulta', origin).href
  const message = [
    'Martini Cell: seguimiento de tu reparación',
    `Código: ${code}`,
    `Consulta el estado de tu equipo en: ${consultationUrl}`,
    'Guarda el código para futuras consultas.',
  ].join('\n')

  return {
    consultationUrl,
    message,
    emailUrl: `mailto:?subject=${encodeURIComponent(`Martini Cell: seguimiento ${code}`)}&body=${encodeURIComponent(message)}`,
    whatsappUrl: `https://wa.me/?text=${encodeURIComponent(message)}`,
  }
}
