import assert from 'node:assert/strict'
import { test } from 'node:test'

import { buildTrackingShare } from '../src/utils/trackingShare.js'

test('el mensaje entrega únicamente código y ruta pública sin datos internos', () => {
  const result = buildTrackingShare('MC-123456', 'https://martini.example.com/panel')

  assert.equal(result.consultationUrl, 'https://martini.example.com/consulta')
  assert.match(result.message, /MC-123456/)
  assert.match(result.message, /https:\/\/martini\.example\.com\/consulta/)
  assert.doesNotMatch(result.message, /cliente|diagnóstico|costo|fotografías|IMEI/i)
})

test('el correo y WhatsApp preservan el texto completo al codificar el enlace', () => {
  const result = buildTrackingShare('MC-A&B', 'https://martini.example.com')
  const email = new URL(result.emailUrl)
  const whatsapp = new URL(result.whatsappUrl)

  assert.equal(email.searchParams.get('body'), result.message)
  assert.equal(whatsapp.searchParams.get('text'), result.message)
  assert.equal(email.searchParams.get('subject'), 'Martini Cell: seguimiento MC-A&B')
  assert.equal(email.pathname, '')
})
