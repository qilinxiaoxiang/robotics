// Preview only: prints the audio bench as JSON (bundled and run by build_preview.mjs).
import path from 'node:path';
import { audioBenches } from './bench-audio';
process.stdout.write(JSON.stringify(audioBenches(process.argv[2] || path.resolve(process.cwd(), '../../parts'))));
