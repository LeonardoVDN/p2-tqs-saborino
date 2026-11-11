// Primeira mensagem de erro devolvida pela API, ou a mensagem padrão.
export function mensagemDaApi(erro, padrao) {
  const dados = erro?.response?.data
  if (typeof dados?.detail === 'string') return dados.detail
  const primeira = dados && typeof dados === 'object' ? Object.values(dados).flat()[0] : null
  return typeof primeira === 'string' ? primeira : padrao
}
