#!/bin/bash
#
# SCRIPT FINAL E DEFINITIVO: Usa o comando 'grep' para comparação,
# que é mais robusto e não depende de ordenação (locale).
#

# --- CONFIGURAÇÃO ---
CSV_COM_PROJETOS_PARA_MANTER="lista-testes.csv"
PASTA_RAIZ_DOS_PROJETOS="projetos-clonados"
# --- FIM DA CONFIGURAÇÃO ---

# Nomes de arquivos temporários
LISTA_PARA_MANTER_TEMP=$(mktemp)
LISTA_ATUAL_TEMP=$(mktemp)
LISTA_PARA_APAGAR_TEMP=$(mktemp)

# Função para limpar os arquivos temporários ao sair
cleanup() {
  rm -f "$LISTA_PARA_MANTER_TEMP" "$LISTA_ATUAL_TEMP" "$LISTA_PARA_APAGAR_TEMP"
}
trap cleanup EXIT

# Validações
if [ ! -f "$CSV_COM_PROJETOS_PARA_MANTER" ]; then
  echo "ERRO: O arquivo CSV '$CSV_COM_PROJETOS_PARA_MANTER' não foi encontrado."
  exit 1
fi
if [ ! -d "$PASTA_RAIZ_DOS_PROJETOS" ]; then
  echo "ERRO: A pasta de projetos '$PASTA_RAIZ_DOS_PROJETOS' não foi encontrada."
  exit 1
fi

echo "--- Passo 1: Gerando lista de projetos para MANTER (formato padrão 'organizacao/projeto')..."
while IFS= read -r filepath; do
  if [[ -n "$filepath" && "$filepath" != "caminho_do_arquivo" ]]; then
    echo "$filepath" | cut -d'/' -f2-3 >> "$LISTA_PARA_MANTER_TEMP"
  fi
done < "$CSV_COM_PROJETOS_PARA_MANTER"
sort -u -o "$LISTA_PARA_MANTER_TEMP" "$LISTA_PARA_MANTER_TEMP"
echo "Encontrados $(wc -l < "$LISTA_PARA_MANTER_TEMP") projetos únicos para manter."
echo ""

echo "--- Passo 2: Gerando lista de projetos ATUAIS (formato padrão 'organizacao/projeto')..."
find "$PASTA_RAIZ_DOS_PROJETOS" -mindepth 2 -maxdepth 2 -type d | sed "s|^$PASTA_RAIZ_DOS_PROJETOS/||" | sort > "$LISTA_ATUAL_TEMP"
echo "Encontrados $(wc -l < "$LISTA_ATUAL_TEMP") projetos no total no disco."
echo ""

echo "--- Passo 3: Comparando as listas com método robusto (grep)..."
# --- ESTA É A MUDANÇA PRINCIPAL ---
# "grep -v -x -f ARQUIVO1 ARQUIVO2" significa:
# Mostre-me as linhas no ARQUIVO2 que NÃO (-v) correspondem exatamente (-x) a nenhuma linha do ARQUIVO1.
grep -v -x -f "$LISTA_PARA_MANTER_TEMP" "$LISTA_ATUAL_TEMP" > "$LISTA_PARA_APAGAR_TEMP"

# --- PASSO 4: SIMULAÇÃO (DRY RUN) ---
if [ ! -s "$LISTA_PARA_APAGAR_TEMP" ]; then
  echo "✨ TUDO CERTO! Nenhum projeto precisa ser apagado."
  exit 0
fi

echo "#####################################################################"
echo "#                         AVISO IMPORTANTE                          #"
echo "#                  A OPERAÇÃO APAGARÁ DADOS!                        #"
echo "#####################################################################"
echo ""
echo "A simulação encontrou os seguintes projetos para APAGAR (caminho completo):"
echo ""
sed "s|^|$PASTA_RAIZ_DOS_PROJETOS/|" "$LISTA_PARA_APAGAR_TEMP"
echo ""
echo "---------------------------------------------------------------------"
echo "Total de projetos a serem APAGADOS: $(wc -l < "$LISTA_PARA_APAGAR_TEMP")"
echo "---------------------------------------------------------------------"
echo ""

# --- PASSO 5: CONFIRMAÇÃO DO USUÁRIO ---
read -p "Você revisou a lista acima? Para confirmar a exclusão PERMANENTE, digite 'sim, apagar': " confirmacao

if [[ "$confirmacao" == "sim, apagar" ]]; then
  echo ""
  echo "--- INICIANDO EXCLUSÃO PERMANENTE ---"
  while IFS= read -r dir_to_delete_base; do
    full_path_to_delete="$PASTA_RAIZ_DOS_PROJETOS/$dir_to_delete_base"
    if [ -d "$full_path_to_delete" ]; then
      echo "Apagando: $full_path_to_delete"
      rm -rf "$full_path_to_delete"
    fi
  done < "$LISTA_PARA_APAGAR_TEMP"
  echo "--- Limpeza concluída com sucesso! ---"
else
  echo ""
  echo "Operação cancelada. Nenhum arquivo foi apagado."
fi