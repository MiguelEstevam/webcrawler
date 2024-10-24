from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import schedule
import time
import os  
import random

# Constantes para URLs
BASE_URL = 'http://bibtranscolbpes.es.gov.br/mobile/'
RESULT_URL = f'{BASE_URL}resultado.asp'

app = Flask(__name__)

# Função para obter a localização detalhada do livro
def obter_localizacao(detalhe_url):
    try:
        detalhe_response = requests.get(detalhe_url, timeout=10)
        detalhe_response.encoding = 'utf-8'
        detalhe_soup = BeautifulSoup(detalhe_response.text, 'html.parser')

        localizacao_link = detalhe_soup.find('a', class_='link-mobile localizacao')
        if localizacao_link and 'href' in localizacao_link.attrs:
            biblioteca_url = BASE_URL + localizacao_link['href']
            biblioteca_response = requests.get(biblioteca_url, timeout=10)
            biblioteca_response.encoding = 'utf-8'
            biblioteca_soup = BeautifulSoup(biblioteca_response.text, 'html.parser')

            localizacao = biblioteca_soup.find('p', class_='textoBibliotecaDetalhe')
            return localizacao.get_text(strip=True) if localizacao else 'Localização não encontrada'
    except requests.RequestException as e:
        print(f"Erro na requisição de localização: {e}")
    except Exception as e:
        print(f"Erro inesperado ao obter localização: {e}")

    return 'Localização não encontrada'

# Função para buscar livros
def buscar_livros(termo_busca):
    data = {
        'idioma': 'ptbr',
        'acesso': 'web',
        'search': termo_busca,
        'rselcampo': 'palavra_chave',
        'rselmaterial': '-1',
        'rselbiblioteca': '-1',
        'busca': '1'
    }

    try:
        response = requests.post(RESULT_URL, data=data, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        else:
            print(f"Erro ao buscar livros: {response.status_code}")
    except requests.RequestException as e:
        print(f"Erro na requisição HTTP: {e}")
    except Exception as e:
        print(f"Erro inesperado ao buscar livros: {e}")
    
    return None

# Função para processar os resultados e extrair dados dos livros
def processar_livros(soup):
    resultados = []
    try:
        livros = soup.find_all('li')
        for livro in livros:
            try:
                titulo_span = livro.find('span', class_='tituloResultadoBusca')
                if not titulo_span:
                    continue

                titulo = titulo_span.get_text(strip=True)
                detalhes = livro.find_all('p')

                autor = detalhes[1].get_text(strip=True) if len(detalhes) > 1 else 'Autor não encontrado'
                tipo = detalhes[2].get_text(strip=True) if len(detalhes) > 2 else 'Tipo não encontrado'
                codigo = detalhes[3].get_text(strip=True) if len(detalhes) > 3 else 'Código não encontrado'

                detalhe_link = livro.find('a')['href']
                detalhe_url = f"{BASE_URL}{detalhe_link}"

                localizacao = obter_localizacao(detalhe_url)

                resultados.append({
                    'titulo': titulo,
                    'autor': autor,
                    'tipo': tipo,
                    'codigo': codigo,
                    'localizacao': localizacao
                })

            except AttributeError as e:
                print(f"Erro ao acessar um atributo do livro: {e}")
            except Exception as e:
                print(f"Erro inesperado ao processar livro: {e}")

    except Exception as e:
        print(f"Erro ao processar a lista de livros: {e}")

    return resultados

# Lista de gêneros literários
GENEROS_LITERARIOS = ['ficção', 'aventura', 'romance', 'história', 'fantasia', 'biografia', 'poesia', 'mistério']

# Função para gerar recomendações e salvar em um arquivo txt com nome único
def gerar_recomendacoes():
    termo_busca = random.choice(GENEROS_LITERARIOS)

    print(f"Buscando recomendações para o gênero: {termo_busca}")

    soup = buscar_livros(termo_busca)

    if soup:
        resultados = processar_livros(soup)

        resultados = resultados[:5]

        if not os.path.exists("recomendações"):
            os.makedirs("recomendações")

        nome_arquivo = f"recomendações/recomendacoes_{termo_busca}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"

        # Gravando as recomendações no arquivo .txt
        with open(nome_arquivo, 'a', encoding='utf-8') as f:
            f.write(f"Recomendações do gênero '{termo_busca}' - {time.strftime('%Y-%m-%d %H:%M:%S')}:\n")
            for livro in resultados:
                f.write(f"Título: {livro['titulo']}\n")
                f.write(f"Autor: {livro['autor']}\n")
                f.write(f"Tipo: {livro['tipo']}\n")
                f.write(f"Código: {livro['codigo']}\n")
                f.write(f"Localização: {livro['localizacao']}\n")
                f.write("\n")
            f.write("------------\n")

        print(f"Arquivo de recomendações gerado: {nome_arquivo}")
    else:
        print("Erro ao buscar recomendações.")

# Agendar a execução diária da rotina de recomendação
def agendar_rotina_diaria():
    schedule.every().day.at("09:20").do(gerar_recomendacoes)

    # Loop que verifica o agendamento
    while True:
        schedule.run_pending()
        time.sleep(60)  

@app.route('/', methods=['GET', 'POST'])
def index():
    resultados = []

    if request.method == 'POST':
        termo_busca = request.form['termo_busca']
        soup = buscar_livros(termo_busca)

        if soup:
            resultados = processar_livros(soup)
        else:
            print("Erro ao buscar os livros.")

    return render_template('index.html', resultados=resultados)

if __name__ == '__main__':
    import threading
    agendamento_thread = threading.Thread(target=agendar_rotina_diaria)
    agendamento_thread.start()

    app.run(debug=True, port=5001)
