import { expect, test } from 'vitest'
import { ApiError, readNDJSON } from './api'

test('NDJSON reconstructs split lines and multibyte Chinese characters', async () => {
  const bytes = new TextEncoder().encode('{"type":"status","message":"处理中"}\n{"type":"final","text":"你好"}')
  const chunks = Array.from(bytes, (byte) => new Uint8Array([byte]))
  const body = new ReadableStream({start(controller) {chunks.forEach((chunk) => controller.enqueue(chunk)); controller.close()}})
  const events = []
  for await (const event of readNDJSON(new Response(body))) events.push(event)
  expect(events).toEqual([{type:'status',message:'处理中'}, {type:'final',text:'你好'}])
})

test('HTTP error keeps stable code and malformed stream is rejected', async () => {
  const stream = readNDJSON(new Response(JSON.stringify({error:{code:'conversation_not_found',message:'不存在'}}),{status:404}))
  await expect(stream.next()).rejects.toMatchObject({code:'conversation_not_found'})
  const broken = readNDJSON(new Response('{bad}\n'))
  await expect(broken.next()).rejects.toBeInstanceOf(ApiError)
})
