import { join } from 'node:path'
import { renderPlist, type PlistInput } from './render.js'

export const INGEST_LABEL = 'com.foomakers.gilberto.ingest'

export const renderIngest = ({ claude, root }: PlistInput): string =>
  renderPlist({
    label: INGEST_LABEL,
    args: [claude, '-p', '/gilberto-process-ingest'],
    workingDirectory: root,
    watchPaths: [join(root, '_ingest')],
  })
