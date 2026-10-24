import { deflateSync } from 'node:zlib'
import { writeFileSync } from 'node:fs'

const size = 1024
const pixels = Buffer.alloc(size * size * 4)
const background = [244, 245, 247]
const blue = [10, 132, 255]

for (let offset = 0; offset < pixels.length; offset += 4) {
  pixels[offset] = background[0]
  pixels[offset + 1] = background[1]
  pixels[offset + 2] = background[2]
  pixels[offset + 3] = 255
}

const curves = [
  [[8, 34], [14, 34], [15, 21], [20, 21]],
  [[20, 21], [25, 21], [25, 44], [30, 44]],
  [[30, 44], [35, 44], [35, 12], [41, 12]],
  [[41, 12], [47, 12], [46, 50], [52, 50]],
  [[52, 50], [56, 50], [57, 39], [60, 34]],
]

function cubic([p0, p1, p2, p3], t) {
  const u = 1 - t
  const a = u * u * u
  const b = 3 * u * u * t
  const c = 3 * u * t * t
  const d = t * t * t
  return [
    (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0]) * 16,
    (a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]) * 16,
  ]
}

function paintDisc(cx, cy, radius) {
  const left = Math.max(0, Math.floor(cx - radius - 1))
  const right = Math.min(size - 1, Math.ceil(cx + radius + 1))
  const top = Math.max(0, Math.floor(cy - radius - 1))
  const bottom = Math.min(size - 1, Math.ceil(cy + radius + 1))

  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      const distance = Math.hypot(x + 0.5 - cx, y + 0.5 - cy)
      const coverage = Math.max(0, Math.min(1, radius + 0.5 - distance))
      if (coverage === 0) continue
      const offset = (y * size + x) * 4
      for (let channel = 0; channel < 3; channel += 1) {
        pixels[offset + channel] = Math.round(
          pixels[offset + channel] * (1 - coverage) + blue[channel] * coverage,
        )
      }
    }
  }
}

for (const curve of curves) {
  for (let step = 0; step <= 240; step += 1) {
    const [x, y] = cubic(curve, step / 240)
    paintDisc(x, y, 32)
  }
}

const crcTable = Array.from({ length: 256 }, (_, value) => {
  let crc = value
  for (let bit = 0; bit < 8; bit += 1) {
    crc = (crc & 1) ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1
  }
  return crc >>> 0
})

function crc32(buffer) {
  let crc = 0xffffffff
  for (const byte of buffer) crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

function chunk(type, data) {
  const name = Buffer.from(type)
  const length = Buffer.alloc(4)
  length.writeUInt32BE(data.length)
  const checksum = Buffer.alloc(4)
  checksum.writeUInt32BE(crc32(Buffer.concat([name, data])))
  return Buffer.concat([length, name, data, checksum])
}

const header = Buffer.alloc(13)
header.writeUInt32BE(size, 0)
header.writeUInt32BE(size, 4)
header[8] = 8
header[9] = 6

const scanlines = Buffer.alloc((size * 4 + 1) * size)
for (let y = 0; y < size; y += 1) {
  const rowOffset = y * (size * 4 + 1)
  scanlines[rowOffset] = 0
  pixels.copy(scanlines, rowOffset + 1, y * size * 4, (y + 1) * size * 4)
}

const png = Buffer.concat([
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
  chunk('IHDR', header),
  chunk('IDAT', deflateSync(scanlines, { level: 9 })),
  chunk('IEND', Buffer.alloc(0)),
])

writeFileSync(new URL('../SynovaIOS/Synova/Assets.xcassets/AppIcon.appiconset/SynovaIcon.png', import.meta.url), png)
