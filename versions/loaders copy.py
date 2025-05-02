
from langchain_community.document_loaders import (WebBaseLoader,
                                                  YoutubeLoader,
                                                  CSVLoader,
                                                  PyPDFLoader,
                                                  TextLoader
                                                  )


import os
import tempfile
import re
import urllib.parse
import requests
import moviepy.editor as mp
from pydub import AudioSegment
import speech_recognition as sr
import datetime
import base64
import streamlit as st
from pytube import YouTube
import gdown


from dotenv import load_dotenv
from notion_client import Client

#Load environment variables
load_dotenv()

def extrair_id_video_youtube(url):
    """Extrai o ID do vídeo a partir de um link do YouTube"""
    # Padrões possíveis de URLs do YouTube
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/e\/|youtube\.com\/user\/.+\/|youtube\.com\/user\/\w+#p\/u\/\d+\/|youtube\.com\/\?v=|youtube\.com\/\?feature=player_embedded&v=|youtube\.com\/user\/.+\/\?v=|youtube\.com\/user\/.+\&v=|youtube\.com\/attribution_link\?a=.+?&u=%2Fwatch%3Fv%3D|youtube\.com\/attribution_link\?u=%2Fwatch%3Fv%3D)([^"&?\/\s]{11})',
        r'(?:youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/e\/)([^"&?\/\s]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Se ainda não encontrou, tenta extrair de URLs curtas
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.netloc == 'youtu.be':
        return parsed_url.path[1:]
    
    # Se não for uma URL completa, verifica se o próprio texto é um ID válido do YouTube
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    return None

def extrair_id_arquivo_google_drive(url):
    """Extrai o ID do arquivo a partir de um link do Google Drive"""
    # Formato comum de URL do Google Drive
    pattern = r'(?:/file/d/|/open\?id=|id=)([a-zA-Z0-9_-]{25,})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    
    # Para links de compartilhamento com /view?usp=sharing
    parsed_url = urllib.parse.urlparse(url)
    if 'drive.google.com' in parsed_url.netloc:
        query_params = urllib.parse.parse_qs(parsed_url.query)
        path_parts = parsed_url.path.split('/')
        
        if 'id' in query_params:
            return query_params['id'][0]
        elif len(path_parts) >= 3 and path_parts[-2] == 'd':
            return path_parts[-1]
    
    return None



def carrega_site(url):
    loader = WebBaseLoader(url)
    lista_documentos = loader.load()
    documento = '\n\n'.join([doc.page_content for doc in lista_documentos])
    return  documento


def carrega_youtube(url):
    """Carrega e transcreve conteúdo de um vídeo do YouTube"""
    try:
        with st.spinner('Baixando vídeo do YouTube...'):
            id_video = extrair_id_video_youtube(url)
            if not id_video:
                return f"Erro: URL ou ID do YouTube inválido: {url}"
            
            # Criar diretório temporário para download
            temp_dir = tempfile.mkdtemp()
            yt = YouTube(f"https://www.youtube.com/watch?v={id_video}")
            
            # Obter informações do vídeo
            titulo = yt.title
            duracao = yt.length
            
            # Baixar o vídeo (apenas áudio para economizar tempo)
            audio_stream = yt.streams.filter(only_audio=True).first()
            audio_path = audio_stream.download(output_path=temp_dir)
            
            # Converter para wav para processamento
            wav_path = os.path.join(temp_dir, 'audio.wav')
            audio = AudioSegment.from_file(audio_path)
            audio.export(wav_path, format="wav")
        
        with st.spinner('Transcrevendo áudio do YouTube...'):
            # Usar o mesmo método de transcrição que usamos para MP4
            recognizer = sr.Recognizer()
            
            # Dividir áudio em chunks para melhor reconhecimento
            sound = AudioSegment.from_wav(wav_path)
            chunks = []
            chunk_size = 60000  # 60 segundos por chunk
            for i in range(0, len(sound), chunk_size):
                chunk = sound[i:i+chunk_size]
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                chunk.export(chunk_path, format="wav")
                chunks.append(chunk_path)
            
            transcricao = ""
            for i, chunk_path in enumerate(chunks):
                with sr.AudioFile(chunk_path) as source:
                    audio_data = recognizer.record(source)
                    try:
                        parte_texto = recognizer.recognize_google(audio_data, language="pt-BR")
                        transcricao += parte_texto + " "
                    except sr.UnknownValueError:
                        transcricao += "[Trecho inaudível] "
                    except sr.RequestError:
                        transcricao += "[Erro na API de reconhecimento] "
                
                # Limpar arquivo temporário
                os.remove(chunk_path)
            
            # Salvar a transcrição na sessão para download posterior
            st.session_state[f'transcricao_youtube_{id_video}'] = transcricao
            st.session_state[f'duracao_youtube_{id_video}'] = duracao
            st.session_state[f'titulo_youtube_{id_video}'] = titulo
            st.session_state[f'mostrar_download_youtube_{id_video}'] = True
            
            # Limpar arquivos temporários
            os.remove(wav_path)
            os.remove(audio_path)
            os.rmdir(temp_dir)
            
            return transcricao.strip()
    except Exception as e:
        st.error(f"Erro ao processar o vídeo do YouTube: {str(e)}")
        return f"Erro na transcrição do YouTube: {str(e)}"

def carrega_google_drive(url):
    """Carrega conteúdo de um arquivo do Google Drive"""
    try:
        with st.spinner('Baixando arquivo do Google Drive...'):
            file_id = extrair_id_arquivo_google_drive(url)
            if not file_id:
                return f"Erro: URL do Google Drive inválida: {url}"
            
            # Criar diretório temporário para download
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, 'downloaded_file')
            
            # Baixar o arquivo
            gdown.download(f"https://drive.google.com/uc?id={file_id}", output_path, quiet=False)
            
            # Determinar o tipo de arquivo pelo conteúdo
            file_type = None
            with open(output_path, 'rb') as f:
                header = f.read(4)
                if header.startswith(b'%PDF'):
                    file_type = 'pdf'
                    output_with_ext = output_path + '.pdf'
                elif header.startswith(b'\x00\x00\x00') or header.startswith(b'\x00\x00\x01'):
                    file_type = 'mp4'
                    output_with_ext = output_path + '.mp4'
            
            # Se não identificado pelo cabeçalho, tentar pela extensão na URL
            if not file_type:
                if 'name=' in url:
                    name_part = re.search(r'name=([^&]+)', url)
                    if name_part:
                        file_name = name_part.group(1)
                        if '.' in file_name:
                            ext = file_name.split('.')[-1].lower()
                            if ext in ['pdf', 'txt', 'csv', 'mp4']:
                                file_type = ext
                                output_with_ext = output_path + '.' + ext
            
            # Se ainda não identificado, verificar pelo mimetype
            if not file_type:
                import magic
                mime = magic.Magic(mime=True)
                file_mime = mime.from_file(output_path)
                if 'pdf' in file_mime:
                    file_type = 'pdf'
                    output_with_ext = output_path + '.pdf'
                elif 'text' in file_mime:
                    file_type = 'txt'
                    output_with_ext = output_path + '.txt'
                elif 'csv' in file_mime:
                    file_type = 'csv'
                    output_with_ext = output_path + '.csv'
                elif 'video' in file_mime or 'mp4' in file_mime:
                    file_type = 'mp4'
                    output_with_ext = output_path + '.mp4'
            
            # Renomear o arquivo com a extensão correta
            if file_type:
                os.rename(output_path, output_with_ext)
                
                # Processar de acordo com o tipo de arquivo
                if file_type == 'pdf':
                    return carrega_pdf(output_with_ext)
                elif file_type == 'txt':
                    return carrega_txt(output_with_ext)
                elif file_type == 'csv':
                    return carrega_csv(output_with_ext)
                elif file_type == 'mp4':
                    # Para MP4, criar um objeto similar ao UploadedFile do Streamlit
                    class MockUploadedFile:
                        def __init__(self, path, name):
                            self.path = path
                            self.name = name
                            
                        def read(self):
                            with open(self.path, 'rb') as f:
                                return f.read()
                    
                    mock_file = MockUploadedFile(output_with_ext, f"gdrive_{file_id}.mp4")
                    transcricao, duracao = transcrever_mp4(mock_file)
                    
                    # Salvar dados para download
                    st.session_state[f'transcricao_gdrive_{file_id}'] = transcricao
                    st.session_state[f'duracao_gdrive_{file_id}'] = duracao
                    st.session_state[f'mostrar_download_gdrive_{file_id}'] = True
                    
                    return transcricao
            else:
                return f"Erro: Tipo de arquivo não suportado do Google Drive: {url}"
    except Exception as e:
        st.error(f"Erro ao processar o arquivo do Google Drive: {str(e)}")
        return f"Erro ao processar arquivo do Google Drive: {str(e)}"



def carrega_csv(caminho):
    loader = CSVLoader(caminho)
    lista_documentos = loader.load()
    documento = '\n\n'.join([doc.page_content for doc in lista_documentos])
    return  documento


def carrega_pdf(caminho):
    loader = PyPDFLoader(caminho)
    lista_documentos = loader.load()
    documento = '\n\n'.join([doc.page_content for doc in lista_documentos])
    return  documento


def carrega_txt(caminho):
    loader = TextLoader(caminho)
    lista_documentos = loader.load()
    documento = '\n\n'.join([doc.page_content for doc in lista_documentos])
    return  documento


def carrega_notion(notion_page_id=None):
    """
    Load content from a specific Notion page or database using API key from environment variables
    
    Args:
        notion_page_id (str, optional): The ID of the Notion page or database to load.
                                       If None, will use the ID from .env
    
    Returns:
        str: Extracted text content from the Notion page or database
    """
    try:
        # Get Notion API key from environment variables
        notion_api_key = os.getenv('NOTION_API_KEY')
        
        # Check if API key is available
        if not notion_api_key:
            return "Erro: Notion API Key não encontrada no arquivo .env"
        
        # If no page ID is provided, try to get it from environment variables
        if not notion_page_id:
            notion_page_id = os.getenv('NOTION_PAGE_ID')
            
        # Check if page ID is available
        if not notion_page_id:
            return "Erro: ID da página ou banco de dados do Notion não fornecido"
        
        # Initialize Notion client
        notion = Client(auth=notion_api_key)
        
        # Try to determine if the ID is for a page or database
        try:
            # First try to retrieve as a page
            notion.pages.retrieve(page_id=notion_page_id)
            is_database = False
        except Exception:
            try:
                # If not a page, try as a database
                notion.databases.retrieve(database_id=notion_page_id)
                is_database = True
            except Exception as e:
                return f"Erro: ID fornecido não é válido como página ou banco de dados: {str(e)}"
        
        text_content = []
        
        
        # Handle page content
        if not is_database:
            # Extract text content from page blocks
            page_content = notion.blocks.children.list(block_id=notion_page_id)
            
            # Process page blocks
            for block in page_content['results']:
                block_type = block.get('type')
                if block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3', 
                                 'bulleted_list_item', 'numbered_list_item', 'to_do', 
                                 'quote', 'callout']:
                    # Extract text from different block types
                    text = block.get(block_type, {}).get('rich_text', [])
                    if text:
                        text_content.append(''.join([t.get('plain_text', '') for t in text]))
        
        # Handle database content
        else:
            # Query database entries with pagination
            #text_content = []
            has_more = True
    
            start_cursor = None
            while has_more:
                # Adicione um page_size para controlar quantidade de registros

                database_entries = notion.databases.query(
                    database_id=notion_page_id, 
                    start_cursor=start_cursor
                    #page_size=300
                    )
                ''' 1-Paginação: Adicionei um loop while True para lidar com a paginação dos resultados do banco de dados. A função notion.databases.query é chamada repetidamente até que todos os resultados sejam recuperados.
                2-Cursor: Usei start_cursor para rastrear a posição atual na paginação. Se houver mais páginas de resultados (has_more), o cursor é atualizado para next_cursor e a consulta continua.
                3-Processamento de Propriedades: O processamento das propriedades de cada entrada do banco de dados permanece o mesmo, mas agora é garantido que todos os registros sejam processados.
                '''   
                print(f"Total de registros recuperados: {len(database_entries['results'])}")


                  # Debug: Print the raw response from the API
                if not database_entries['results']:
                    break # break if no results       
                         
                # Process each database row
                for entry in database_entries['results']:
                    row_content = []
                    properties = entry.get('properties', {})
                    
                    # Process each property in the row
                    for prop_name, prop_data in properties.items():
                        prop_type = prop_data.get('type')
                        
                        # Handle different property types
                        if prop_type == 'title':
                            title_text = prop_data.get('title', [])
                            if title_text:
                                row_content.append(f"{prop_name}: {''.join([t.get('plain_text', '') for t in title_text])}")
                        
                        elif prop_type == 'rich_text':
                            rich_text = prop_data.get('rich_text', [])
                            if rich_text:
                                row_content.append(f"{prop_name}: {''.join([t.get('plain_text', '') for t in rich_text])}")
                        
                        elif prop_type == 'number':
                            number = prop_data.get('number')
                            if number is not None:
                                row_content.append(f"{prop_name}: {number}")
                        
                        elif prop_type == 'select':
                            select = prop_data.get('select', {})
                            if select and select.get('name'):
                                row_content.append(f"{prop_name}: {select.get('name')}")
                        
                        elif prop_type == 'multi_select':
                            multi_select = prop_data.get('multi_select', [])
                            if multi_select:
                                values = [item.get('name', '') for item in multi_select if item.get('name')]
                                if values:
                                    row_content.append(f"{prop_name}: {', '.join(values)}")
                        
                        elif prop_type == 'date':
                            date = prop_data.get('date', {})
                            if date and date.get('start'):
                                date_text = date.get('start')
                                if date.get('end'):
                                    date_text += f" - {date.get('end')}"
                                row_content.append(f"{prop_name}: {date_text}")
                        
                        elif prop_type == 'checkbox':
                            checkbox = prop_data.get('checkbox')
                            if checkbox is not None:
                                row_content.append(f"{prop_name}: {'Sim' if checkbox else 'Não'}")
                    
                    # Add the row content as a paragraph
                    if row_content:
                        text_content.append(' | '.join(row_content))
                
                # Check if there are more pages of results
                if not database_entries.get('has_more'):
                    break
                has_more = database_entries.get('has_more', False)
                start_cursor = database_entries.get('next_cursor')
        
        # Return error message if no content was found
        if not text_content:
            return "Aviso: Nenhum conteúdo de texto encontrado na página ou banco de dados do Notion"
            
        return '\n\n'.join(text_content)
    
    except Exception as e:
        return f"Erro ao carregar conteúdo do Notion: {str(e)}"
        
def transcrever_mp4(arquivo_mp4):
    """
    Extrai o áudio de um arquivo MP4 e realiza a transcrição do conteúdo falado.
    Retorna a transcrição e a duração do vídeo.
    """
    try:
        with st.spinner('Extraindo áudio do vídeo...'):
            # Salvar o arquivo temporariamente
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                temp_video.write(arquivo_mp4.read())
                video_path = temp_video.name
            
            # Extrair áudio do vídeo
            video = mp.VideoFileClip(video_path)
            duracao_total = video.duration
            audio_path = video_path.replace('.mp4', '.wav')
            video.audio.write_audiofile(audio_path, codec='pcm_s16le')
            video.close()
            
        with st.spinner('Transcrevendo áudio...'):
            # Converter para formato compatível com speech_recognition
            sound = AudioSegment.from_wav(audio_path)
            
            # Usando reconhecimento de fala
            recognizer = sr.Recognizer()
            
            # Dividir áudio em chunks para melhor reconhecimento
            chunks = []
            chunk_size = 60000  # 60 segundos por chunk
            for i in range(0, len(sound), chunk_size):
                chunk = sound[i:i+chunk_size]
                chunk_path = f"{audio_path.replace('.wav', '')}_{i}.wav"
                chunk.export(chunk_path, format="wav")
                chunks.append(chunk_path)
            
            transcricao = ""
            for i, chunk_path in enumerate(chunks):
                with sr.AudioFile(chunk_path) as source:
                    audio_data = recognizer.record(source)
                    try:
                        parte_texto = recognizer.recognize_google(audio_data, language="pt-BR")
                        transcricao += parte_texto + " "
                    except sr.UnknownValueError:
                        transcricao += "[Trecho inaudível] "
                    except sr.RequestError:
                        transcricao += "[Erro na API de reconhecimento] "
                
                # Limpar arquivos temporários
                os.remove(chunk_path)
                
            # Limpar arquivos temporários
            os.remove(audio_path)
            os.remove(video_path)
            
            # Salvar a transcrição na sessão para download posterior
            nome_arquivo = arquivo_mp4.name.replace('.mp4', '')
            st.session_state[f'transcricao_{nome_arquivo}'] = transcricao
            st.session_state[f'duracao_{nome_arquivo}'] = duracao_total
            
            return transcricao.strip(), duracao_total
    except Exception as e:
        st.error(f"Erro ao processar o arquivo MP4: {str(e)}")
        return f"Erro na transcrição: {str(e)}", 0

def gerar_arquivo_srt(transcricao, duracao_total):
    """
    Converte a transcrição em formato SRT com timestamps.
    """
    # Dividir o texto em segmentos para criar legendas
    palavras = transcricao.split()
    segmentos = []
    
    # Criar segmentos de aproximadamente 10 palavras
    tamanho_segmento = 10
    for i in range(0, len(palavras), tamanho_segmento):
        segmento = " ".join(palavras[i:i+tamanho_segmento])
        segmentos.append(segmento)
    
    # Calcular duracao média por segmento
    tempo_por_segmento = duracao_total / len(segmentos) if segmentos else 0
    
    # Formatar como SRT
    conteudo_srt = ""
    for i, segmento in enumerate(segmentos):
        numero = i + 1
        tempo_inicio = i * tempo_por_segmento
        tempo_fim = (i + 1) * tempo_por_segmento
        
        # Formatar tempos no formato SRT (HH:MM:SS,mmm)
        inicio_formatado = str(datetime.timedelta(seconds=tempo_inicio)).replace('.', ',')
        if ',' not in inicio_formatado:
            inicio_formatado += ',000'
        
        fim_formatado = str(datetime.timedelta(seconds=tempo_fim)).replace('.', ',')
        if ',' not in fim_formatado:
            fim_formatado += ',000'
        
        # Adicionar zeros à esquerda para garantir o formato correto (HH:MM:SS)
        if len(inicio_formatado.split(':')[0]) == 1:
            inicio_formatado = '0' + inicio_formatado
        if len(fim_formatado.split(':')[0]) == 1:
            fim_formatado = '0' + fim_formatado
        
        conteudo_srt += f"{numero}\n{inicio_formatado} --> {fim_formatado}\n{segmento}\n\n"
    
    return conteudo_srt

def download_link(conteudo, nome_arquivo, texto_link):
    """
    Gera um link para download de um arquivo de texto.
    """
    b64 = base64.b64encode(conteudo.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{nome_arquivo}">{texto_link}</a>'
    return href

def mostrar_opcoes_download(nome_arquivo_base, transcricao, duracao):
    """
    Exibe opções para download da transcrição em formatos .txt e .srt
    """
    st.subheader(f"Download da transcrição: {nome_arquivo_base}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            download_link(transcricao, f"{nome_arquivo_base}.txt", "📄 Baixar transcrição em formato .txt"),
            unsafe_allow_html=True
        )
    
    with col2:
        conteudo_srt = gerar_arquivo_srt(transcricao, duracao)
        st.markdown(
            download_link(conteudo_srt, f"{nome_arquivo_base}.srt", "🎬 Baixar legendas em formato .srt"),
            unsafe_allow_html=True
        )
