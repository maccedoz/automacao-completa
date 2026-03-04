import pandas as pd
import subprocess
import os

localDaPasta = "projects-sheets"
indice = 1 

def clonar_repositorios():

    try:
        pastaComListaProjetos = os.listdir(localDaPasta)
    except FileNotFoundError:
        print(f"ERRO: A pasta '{localDaPasta}' não foi encontrada.")
        return

    quantidade = len(pastaComListaProjetos)
    for i in range(quantidade):
        excelNameArchive = pastaComListaProjetos[i]
        
        if not excelNameArchive.endswith(('.xlsx', '.xls')):
            continue

        caminho_completo_excel = os.path.join(localDaPasta, excelNameArchive)
        nome_base_destino = os.path.splitext(excelNameArchive)[0]
        destiny = os.path.join(localDaPasta, nome_base_destino)
        
        try:
            df = pd.read_csv(caminho_completo_excel, header=None)
            links = df[indice].dropna().tolist()

        except KeyError:
            print(f"ERRO: A coluna de índice {indice} não foi encontrada na planilha '{excelNameArchive}'.")
            continue
        except Exception as e:
            print(f"ERRO ao ler o arquivo '{excelNameArchive}': {e}")
            continue

        if not links:
            print(f"Nenhum link encontrado na planilha '{excelNameArchive}'.")
            continue

        if not os.path.exists(destiny):
            os.makedirs(destiny)
        
        print(f"\nProcessando '{excelNameArchive}': Encontrados {len(links)} repositórios para clonar.")
        print(f"Os projetos serão salvos em: '{os.path.abspath(destiny)}'")

        erros = 0
        sucessos = 0

        for link in links:
            if not isinstance(link, str) or not link.startswith('http'):
                print(f"AVISO: Ignorando entrada inválida: '{link}'")
                continue

            try:
                print(f"--- Clonando: {link} ---")
                subprocess.run(['git', 'clone', link], cwd=destiny, check=True, capture_output=True, text=True)
                print(f"SUCESSO: Repositório clonado com sucesso!")
                sucessos += 1
            except subprocess.CalledProcessError:
                print(f"ERRO ao clonar {link}. O repositório pode ser privado, já existir ou o link está incorreto.")
                erros += 1
            except FileNotFoundError:
                print("ERRO: O comando 'git' não foi encontrado.")
                print("Por favor, certifique-se de que o Git está instalado e acessível no seu sistema.")
                return

        print("==========================================")
        print(f"Finalizado para '{excelNameArchive}'!")
        print(f"Total de sucessos: {sucessos}")
        print(f"Total de erros: {erros}")
        print("==========================================")


if __name__ == '__main__':
    clonar_repositorios()