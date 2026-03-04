# -*- coding: utf-8 -*-
import sqlite3
import os
import re
import chardet
from pathlib import Path
import csv

# --- CONFIGURAÇÕES GLOBAIS ---
dbPasta = '../planilhas-testes/metricas2.db'
colunaNomeProjeto = 'projectName'
colunaNomePasta = 'pathFile'
colunaNomeMetodo = 'testSmellMethod'
colunaNomeSmell = 'testSmellName'
arquivoComtests = 'testessmells.csv'

def encontrarMetodosNormais(caminho_arquivo, nome_metodo):
    """
    Localiza o código de um método específico em um arquivo, junto com suas linhas de início e fim.
    """
    if not os.path.exists(caminho_arquivo):
        print(f"AVISO: Arquivo não encontrado em '{caminho_arquivo}'. Pulando este teste.")
        return None
    try:
        with open(caminho_arquivo, 'rb') as f_binary:
            raw_data = f_binary.read()
        resultado_deteccao = chardet.detect(raw_data)
        encoding = resultado_deteccao['encoding'] if resultado_deteccao['encoding'] is not None else 'utf-8'
        conteudo_arquivo = raw_data.decode(encoding, errors='ignore') # Adicionado 'errors' para mais robustez
        linhas_arquivo = conteudo_arquivo.splitlines()
    except Exception as e:
        print(f"ERRO: Falha ao ler ou decodificar o arquivo '{caminho_arquivo}'. Detalhe: {e}. Pulando este teste.")
        return None
    
    # Padrão para encontrar a assinatura do método de forma mais flexível
    padrao_metodo = re.compile(
        r'^\s*'
        r'(?:@\w+\s*)*'  # Anotações (ex: @Test)
        r'(?:public|private|protected)?\s*'
        r'(?:static)?\s*(?:final)?\s*'
        r'(?:\S+|<[^>]+>)\s+'
        + re.escape(nome_metodo) +
        r'\s*\(',
        re.MULTILINE
    )
    
    match = padrao_metodo.search(conteudo_arquivo)
    if not match:
        print(f"  -> AVISO: Assinatura para o método '{nome_metodo}' não encontrada no arquivo.")
        return None
    
    indice_assinatura = conteudo_arquivo.count('\n', 0, match.start())
    contador_chaves = 0
    corpo_iniciado = False
    indice_linha_final = -1
    
    for i in range(indice_assinatura, len(linhas_arquivo)):
        linha = linhas_arquivo[i]
        aberturas = linha.count('{')
        fechamentos = linha.count('}')
        
        if not corpo_iniciado and aberturas > 0:
            corpo_iniciado = True
        
        if corpo_iniciado:
            contador_chaves += aberturas
            contador_chaves -= fechamentos
            if contador_chaves <= 0:
                indice_linha_final = i
                break
    
    if indice_linha_final == -1:
        print(f"  -> AVISO: Não foi possível encontrar o fim do método '{nome_metodo}' (chaves desbalanceadas?).")
        return None
        
    linha_inicio = indice_assinatura + 1
    linha_fim = indice_linha_final + 1
    codigo_completo = "\n".join(linhas_arquivo[indice_assinatura : indice_linha_final + 1])
    
    return {
        "codigo": codigo_completo,
        "linha_inicio": linha_inicio,
        "linha_fim": linha_fim
    }

def formatarSaidaNormal(testes_selecionados, arquivoFinal):
    """
    Gera o arquivo de saída formatado para os testes normais.
    """
    print(f"\nSeleção finalizada. {len(testes_selecionados)} testes únicos foram extraídos com sucesso.")
    print(f"Gerando o arquivo de saída '{arquivoFinal}'...")

    with open(arquivoFinal, 'w', encoding='utf-8') as f_out:
        for i, teste in enumerate(testes_selecionados, 1):
            f_out.write(f"TESTE {i}\n")
            f_out.write(f"PROJETO: {teste['projeto']}\n")
            f_out.write(f"ARQUIVO: {teste['caminho']}\n")
            f_out.write(f"LINHAS: {teste['intervalo_linhas']}\n")
            f_out.write("```java\n")
            f_out.write(f"{teste['codigo'].strip()}\n")
            f_out.write("```\n\n")

    print("Processo concluído com sucesso!")
    print(f"Verifique o arquivo '{arquivoFinal}' na mesma pasta onde o script foi executado.")
    
def processArquivoNormal(resultados):
    """
    Processa os resultados da query para extrair métodos de teste únicos.
    """
    projetos_com_metodos = {}
    for proj_name_do_db, caminho_arquivo, nome_metodo in resultados:
        nome_projeto_real = proj_name_do_db
        try:
            partes_caminho = Path(caminho_arquivo).parts
            idx = partes_caminho.index('.jnose_projects')
            if idx + 1 < len(partes_caminho):
                nome_projeto_real = partes_caminho[idx + 1]
        except (ValueError, IndexError):
            pass
        
        if nome_projeto_real not in projetos_com_metodos:
            projetos_com_metodos[nome_projeto_real] = []
        projetos_com_metodos[nome_projeto_real].append({'caminho': caminho_arquivo, 'metodo': nome_metodo})

    print(f"Processando {len(projetos_com_metodos)} projetos únicos para encontrar 100 testes válidos...")
    testes_selecionados = []
    codigos_ja_vistos = set()
    
    for nome_projeto, metodos_candidatos in projetos_com_metodos.items():
        if len(testes_selecionados) >= 100:
            print("Meta de 100 testes únicos atingida. Finalizando a busca.")
            break

        for metodo_info in metodos_candidatos:
            # CORREÇÃO: Chamada da função com o nome correto
            dados_metodo = encontrarMetodosNormais(metodo_info['caminho'], metodo_info['metodo'])
            
            if dados_metodo:
                codigo_extraido = dados_metodo['codigo']
                codigo_normalizado = re.sub(r'\s+', '', codigo_extraido)

                if codigo_normalizado not in codigos_ja_vistos:
                    print(f"  -> SUCESSO! Método '{metodo_info['metodo']}' extraído do projeto '{nome_projeto}' (código único).")
                    codigos_ja_vistos.add(codigo_normalizado)
                    
                    testes_selecionados.append({
                        'projeto': nome_projeto,
                        'caminho': metodo_info['caminho'],
                        'codigo': dados_metodo['codigo'],
                        'intervalo_linhas': f"{dados_metodo['linha_inicio']}-{dados_metodo['linha_fim']}"
                    })
                    # Para pegar apenas um por projeto, podemos usar o break aqui.
                    # Se quiser continuar no mesmo projeto, remova o break.
                    if len(testes_selecionados) >= 100: break
                else:
                    print(f"  -> AVISO: Método '{metodo_info['metodo']}' ignorado (código duplicado).")
        if len(testes_selecionados) >= 100: break
    
    return testes_selecionados


    """
    Processa os resultados da query para extrair classes de teste únicas.
    """
    projetos_com_arquivos = {}
    for proj_name_do_db, caminho_arquivo, _ in resultados: # Ignora o terceiro valor da tupla
        nome_projeto_real = proj_name_do_db
        try:
            partes_caminho = Path(caminho_arquivo).parts
            idx = partes_caminho.index('.jnose_projects')
            if idx + 1 < len(partes_caminho):
                nome_projeto_real = partes_caminho[idx + 1]
        except (ValueError, IndexError):
            pass
        
        if nome_projeto_real not in projetos_com_arquivos:
            projetos_com_arquivos[nome_projeto_real] = set() # Usar set para evitar caminhos duplicados
        projetos_com_arquivos[nome_projeto_real].add(caminho_arquivo)

    print(f"Processando {len(projetos_com_arquivos)} projetos únicos...")

    classes_selecionadas = []
    codigos_ja_vistos = set()
    
    for nome_projeto, caminhos_candidatos in projetos_com_arquivos.items():
        if len(classes_selecionadas) >= 100:
            print("Meta de 100 classes únicas atingida. Finalizando a busca.")
            break

        for caminho_arquivo in caminhos_candidatos:
            # CORREÇÃO: Chamada da função com o nome correto
            codigo_completo = encontrarLazyTest(caminho_arquivo)
            
            if codigo_completo:
                codigo_normalizado = re.sub(r'\s+', '', codigo_completo)

                if codigo_normalizado not in codigos_ja_vistos:
                    print(f"  -> SUCESSO! Classe extraída do projeto '{nome_projeto}' (código único).")
                    codigos_ja_vistos.add(codigo_normalizado)
                    
                    classes_selecionadas.append({
                        'projeto': nome_projeto,
                        'caminho': caminho_arquivo,
                        'codigo': codigo_completo
                    })
                    if len(classes_selecionadas) >= 100: break
                else:
                    print(f"  -> AVISO: Classe do arquivo '{caminho_arquivo}' ignorada (código duplicado).")
        if len(classes_selecionadas) >= 100: break
        
    return classes_selecionadas

def main():
    """
    Função principal que orquestra a leitura do CSV, a consulta ao DB e a geração dos arquivos.
    """
    nomesTestsSmells = []
    
    if not os.path.exists(arquivoComtests):
        print(f"ERRO CRÍTICO: O arquivo de smells '{arquivoComtests}' não foi encontrado.")
        return

    with open(arquivoComtests, mode='r', encoding='utf-8', newline='') as csvfile:
        leitorCSV = csv.DictReader(csvfile)
        # CORREÇÃO: Obter o nome da primeira coluna dinamicamente
        primeira_coluna_header = leitorCSV.fieldnames[0]
        for linha in leitorCSV:
            nomesTestsSmells.append(linha[primeira_coluna_header])

    for nome in nomesTestsSmells:
        print("\n" + "="*50)
        print(f"PROCESSANDO O TEST SMELL: {nome}")
        print("="*50)

        arquivoFinal = f"{nome.replace(' ', '_')}.txt" # Nome de arquivo mais seguro
        
        if not os.path.exists(dbPasta):
            print(f"ERRO CRÍTICO: O arquivo do banco de dados '{dbPasta}' não foi encontrado.")
            continue # Pula para o próximo smell

        conn = None # Inicializa a conexão como None
        try:
            conn = sqlite3.connect(dbPasta)
            cursor = conn.cursor()

            query1 = f"""
            SELECT
                {colunaNomeProjeto}, {colunaNomePasta}, {colunaNomeMetodo}
            FROM
                testsmells
            GROUP BY
                {colunaNomeProjeto}, {colunaNomePasta}, {colunaNomeMetodo}
            HAVING
                COUNT(DISTINCT {colunaNomeSmell}) = 1 AND MIN({colunaNomeSmell}) = ?;
            """
            
            print("Executando Query 1 (métodos com apenas um smell)...")
            cursor.execute(query1, (nome,))
            resultados = cursor.fetchall()

            if len(resultados) < 10:
                print(f"Testes insuficientes ({len(resultados)}). Buscando métodos em projetos com o smell (Query 2)...")
                
                query2 = f"""
                SELECT
                    {colunaNomeProjeto},
                    {colunaNomePasta},
                    MIN({colunaNomeMetodo})
                FROM
                    testsmells
                WHERE
                    {colunaNomeSmell} = ?
                GROUP BY
                    {colunaNomeProjeto}, {colunaNomePasta};
                """
                
                cursor.execute(query2, (nome,))
                resultados = cursor.fetchall()
            
            print(f"Encontrados {len(resultados)} registros candidatos para processamento.")

            if not resultados:
                print("Nenhum registro encontrado para este smell. Pulando...")
                continue

            testes_selecionados = processArquivoNormal(resultados)
            formatarSaidaNormal(testes_selecionados, arquivoFinal)

        except sqlite3.OperationalError as e:
            print(f"ERRO CRÍTICO no DB: Verifique os nomes das colunas e tabelas. Detalhe: {e}")
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")
        finally:
            if conn:
                conn.close() # Garante que a conexão seja fechada

if __name__ == "__main__":
    main()
