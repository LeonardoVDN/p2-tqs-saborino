// Migração única e deliberadamente estreita: não apaga dados comerciais/UI.
const LEGACY_KEYS = ['saborino_access', 'saborino_refresh']

export function purgeLegacyTokens(storage) {
  try {
    const target = storage || window.localStorage
    if (typeof target?.removeItem !== 'function') return
    for (const key of LEGACY_KEYS) target.removeItem(key)
  } catch {
    // Navegação continua quando storage está proibido pela política do browser.
  }
}

purgeLegacyTokens()
