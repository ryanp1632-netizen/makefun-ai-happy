// ai-happy-01 entry (Node 22, standard library only).
// The picture is rendered ahead of time by render/scene.py (Blender, Cycles) and committed as art/entry.png.
// This program checks it against the gate's rules and writes it, byte for byte, to /output/entry.png.
//
// Outside the grader:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const MAX_BYTES = 1024 * 1024;
const MAX_SIDE = 1024;

const image = readFileSync(new URL('./art/entry.png', import.meta.url));

const isPng = image.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
if (!isPng) throw new Error('art/entry.png is not a PNG');
if (image.length > MAX_BYTES) throw new Error(`art/entry.png is ${image.length} bytes, over the 1 MiB cap`);

const width = image.readUInt32BE(16);
const height = image.readUInt32BE(20);
if (width > MAX_SIDE || height > MAX_SIDE) throw new Error(`art/entry.png is ${width}x${height}, over 1024x1024`);

// The gate wants a whole image: walk every chunk and make sure the file ends with IEND.
let at = 8;
let sawEnd = false;
while (at + 12 <= image.length) {
  const length = image.readUInt32BE(at);
  const type = image.toString('latin1', at + 4, at + 8);
  at += 12 + length;
  if (type === 'IEND') {
    sawEnd = true;
    break;
  }
}
if (!sawEnd || at !== image.length) throw new Error('art/entry.png is truncated or has trailing bytes');

const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, 'entry.png'), image);
