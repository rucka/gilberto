import { installPlugin, PluginInstallError, type InstallResult } from './install.js'
import { marketplaceHas } from './marketplace.js'
import { removePlugin } from './remove.js'
import { resolveSource } from './source.js'
import type { CommandDeps } from '../types.js'
import type { PluginAction, PluginCommandConfig } from './parser.js'

export const pluginPlaceholderMessage = (action: PluginAction): string =>
  `plugin ${action} not yet implemented — Initiative #3 EP Plugin protocol (issue #15)`

const skillsHint = ({ name, skills }: InstallResult, deps: CommandDeps): string[] => {
  if (!skills.length) return []
  return [
    marketplaceHas(name, deps.env)
      ? `${name}: skills present (marketplace)`
      : `${name}: skills not copied, run: /plugin install ${name}`,
  ]
}

function install(config: PluginCommandConfig, deps: CommandDeps): void {
  const [arg] = config.args
  if (!arg) throw new Error('plugin install: missing <name|repo-url>')
  const source = resolveSource(arg, deps.env['GILBERTO_PLUGINS_DIR'])
  const failures: string[] = []
  try {
    for (const dir of source.dirs) {
      try {
        const r = installPlugin(deps.cwd, dir, {
          force: config.force,
          dryRun: config.dryRun,
        })
        const verb = r.dryRun ? 'would install' : 'installed'
        deps.write(`${verb} ${r.name} ${r.version}\n`)
        for (const f of r.files) deps.write(`  ${f}\n`)
        for (const h of skillsHint(r, deps)) deps.write(`${h}\n`)
      } catch (e) {
        if (!(e instanceof PluginInstallError) || source.dirs.length === 1) throw e
        failures.push(e.message)
        deps.logger.error(e.message)
      }
    }
  } finally {
    source.cleanup()
  }
  if (failures.length) throw new Error(`${failures.length} plugin(s) failed to install`)
}

function remove(config: PluginCommandConfig, deps: CommandDeps): void {
  const [name] = config.args
  if (!name) throw new Error('plugin remove: missing <name>')
  const r = removePlugin(deps.cwd, name, { purge: config.purge, dryRun: config.dryRun })
  deps.write(`${r.dryRun ? 'would remove' : 'removed'} ${r.name}\n`)
  for (const f of r.removed) deps.write(`  ${f}\n`)
  for (const f of r.kept) deps.logger.warn(`kept modified file (use --purge to delete): ${f}`)
}

export const handlePluginCommand = async (
  config: PluginCommandConfig,
  deps: CommandDeps,
): Promise<void> => {
  switch (config.action) {
    case 'install':
      return install(config, deps)
    case 'remove':
      return remove(config, deps)
    case 'list':
    case 'enable':
    case 'disable':
    case 'update':
      console.error(pluginPlaceholderMessage(config.action))
      return
    default: {
      const unreachable: never = config.action
      throw new Error(`unknown plugin action: ${String(unreachable)}`)
    }
  }
}
