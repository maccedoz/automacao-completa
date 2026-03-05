#precisariamos de uma integração com o jnose
import subprocess
import sys

import cloning_repositories

REPO_SHEET = "xxxxx"
TESTS_SMELLS = "xxxx"


def find():
    comand_find_one = 'find . -type f -iname "*test*.java" > testessmells.csv'
    comand_find_two = 'find . -type f -iname "*Test*.java" >> testessmells.csv'
    subprocess.run(comand_find_one, shell=True)
    subprocess.run(comand_find_two, shell=True)
    
def main():
    #Primeiro ele clona os repositórios, estes que disponibilizamos a lista no "REPO_SHEET"
    cloning_repositories.clonar_repositorios(REPO_SHEET)
    #Após isso, ele iria rodar o comando find para encontrar os arquivos de teste e gerar um csv

    try:
        subprocess.run(["bash", "apagar_projetos.sh"], check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(1)

    #agora os projetos iriam pra o jnose, ele retornaria csvs e a gente transformaria isso em um banco sqlite
    #a partir disso teria uma query pra pegar tipos de smells mais recorrentes
    #esses testes iriam pra uma planilha e a gente usaria eles futuramente
    #nisso a gente iria coletar x testes de cada tipo usando o buscar testes e gerar um arquivo txt
    #a partir disso a gente usa o automaçao assincrono pra rodar os testes e coletar os resultados 


