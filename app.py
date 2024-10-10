from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# URL da página de busca
url = 'http://bibtranscolbpes.es.gov.br/mobile/resultado.asp'

# Função para obter a localização detalhada do livro
def obter_localizacao(detalhe_url):
    detalhe_response = requests.get(detalhe_url)
    detalhe_response.encoding = 'utf-8'  # Garantir o uso de UTF-8
    detalhe_soup = BeautifulSoup(detalhe_response.text, 'html.parser')

    # Encontrar o link para a página de localização
    localizacao_link = detalhe_soup.find('a', class_='link-mobile localizacao')
    if localizacao_link and 'href' in localizacao_link.attrs:
        # Fazer a requisição para a página de detalhe da biblioteca
        biblioteca_url = "http://bibtranscolbpes.es.gov.br/mobile/" + localizacao_link['href']
        biblioteca_response = requests.get(biblioteca_url)
        biblioteca_response.encoding = 'utf-8'  # Garantir o uso de UTF-8
        biblioteca_soup = BeautifulSoup(biblioteca_response.text, 'html.parser')

        # Extrair a localização
        localizacao = biblioteca_soup.find('p', class_='textoBibliotecaDetalhe')
        return localizacao.get_text(strip=True) if localizacao else 'Localização não encontrada'

    return 'Localização não encontrada'

@app.route('/', methods=['GET', 'POST'])
def index():
    resultados = []
    if request.method == 'POST':
        termo_busca = request.form['termo_busca']
        data = {
            'idioma': 'ptbr',
            'acesso': 'web',
            'search': termo_busca,  # Termo de busca
            'rselcampo': 'palavra_chave',  # Campo de pesquisa
            'rselmaterial': '-1',  # Tipo de material (-1 para todos)
            'rselbiblioteca': '-1',  # Biblioteca (-1 para todas)
            'busca': '1'  # Indica que uma busca foi feita
        }

        # Fazer a requisição HTTP POST com os dados da busca
        response = requests.post(url, data=data)
        response.encoding = 'utf-8'  # Garantir o uso de UTF-8

        # Verificar se a requisição foi bem-sucedida
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            livros = soup.find_all('li')

            for livro in livros:
                try:
                    titulo_span = livro.find('span', class_='tituloResultadoBusca')
                    if not titulo_span:
                        continue  # Ignora livros sem título

                    titulo = titulo_span.get_text(strip=True)
                    detalhes = livro.find_all('p')

                    autor = detalhes[1].get_text(strip=True) if len(detalhes) > 1 else 'Autor não encontrado'
                    tipo = detalhes[2].get_text(strip=True) if len(detalhes) > 2 else 'Tipo não encontrado'
                    codigo = detalhes[3].get_text(strip=True) if len(detalhes) > 3 else 'Código não encontrado'

                    detalhe_link = livro.find('a')['href']
                    detalhe_url = f"http://bibtranscolbpes.es.gov.br/mobile/{detalhe_link}"

                    localizacao = obter_localizacao(detalhe_url)

                    resultados.append({
                        'titulo': titulo,
                        'autor': autor,
                        'tipo': tipo,
                        'codigo': codigo,
                        'localizacao': localizacao
                    })

                except Exception as e:
                    continue

    return render_template('index.html', resultados=resultados)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
