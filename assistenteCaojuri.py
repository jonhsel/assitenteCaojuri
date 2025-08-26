import streamlit as st
import tempfile
from langchain.memory import ConversationBufferMemory

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
#from langchain_deepseek import ChatDeepSeek

from loaders import mostrar_opcoes_download
from loaders import carrega_site, carrega_youtube, carrega_csv, carrega_pdf, carrega_txt, transcrever_mp4, carrega_notion, carrega_google_drive
import os
from dotenv import load_dotenv
from notion_client import Client


from langchain.prompts import ChatPromptTemplate


#Load environment variables
load_dotenv()
#================
#CSS

with open('style.css') as f:
   st.markdown(f'<style>{f.read()}</style', unsafe_allow_html=True)

#################

st.image('images/juria.png')


TIPOS_ARQUIVOS = ['Arquivos .pdf', 'Site', 'Youtube', 'Arquivos .csv', 'Arquivos .txt','Arquivos .mp4', 'Notion', 'Google Drive']

#ARQUIVO_NOTION =['Notion']

CONFIG_MODELOS = {  'OpenAI': 
                            {'modelos': ['gpt-4o-mini', 'gpt-4o'],
                            'chat': ChatOpenAI},
                    'Anthropic':
                            {'modelos':['claude-3-5-haiku-20241022','claude-3-5-sonnet-20241022'],
                             'chat':ChatAnthropic},
                    'Google':
                            {'modelos':['gemini-2.0-flash', 'gemini-2.0-flash-lite-preview-02-05', 'gemini-1.5-flash', 'gemini-1.5-pro'],
                             'chat': ChatGoogleGenerativeAI}
                    #'DeepSeek': {'modelos':['-'],'chat': ChatDeepSeek}
}

MEMORIA = ConversationBufferMemory()

def carrega_arquivo (tipo_arquivo, arquivo):
    documentos = []
    

    if tipo_arquivo == 'Site':
        documento = carrega_site(arquivo)  
        documentos.append(documento)  

    elif tipo_arquivo == 'Youtube':
        documento = carrega_youtube(arquivo)
        documentos.append(documento)  

    elif tipo_arquivo == 'Google Drive':
        documento = carrega_google_drive(arquivo)
        documentos.append(documento)

    elif tipo_arquivo in ['Arquivos .pdf', 'Arquivos .csv', 'Arquivos .txt', 'Arquivos .mp4']:
        for arq in arquivo: # Itera sobre a lista de arquivos
            if tipo_arquivo == 'Arquivos .mp4':
                # Para MP4, trabalhamos diretamente com o arquivo
                transcricao, duracao = transcrever_mp4(arq)
                documento = transcricao
                nome_arquivo_base = arq.name.replace('.mp4', '')
                st.session_state[f'mostrar_download_{nome_arquivo_base}'] = True
                st.session_state[f'transcricao_{nome_arquivo_base}'] = transcricao
                st.session_state[f'duracao_{nome_arquivo_base}'] = duracao
            else:
                with tempfile.NamedTemporaryFile(suffix=f'.{tipo_arquivo.split(".")[-1]}', delete=False) as temp:
                    temp.write(arq.read())
                    nome_temp = temp.name
                if tipo_arquivo == 'Arquivos .pdf':
                    documento = carrega_pdf(nome_temp)
                elif tipo_arquivo == 'Arquivos .csv':
                    documento = carrega_csv(nome_temp)
                elif tipo_arquivo == 'Arquivos .txt':
                    documento = carrega_txt(nome_temp)
            documentos.append(documento)

    elif tipo_arquivo == 'Notion':
          documento = carrega_notion(arquivo)
          documentos.append(documento)

    return documentos


def carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo):

    documento = carrega_arquivo(tipo_arquivo, arquivo)
    

    system_message = ''' Você é JúrIA - Assitente Virtual do CAOJÚRI.
    Você possui acesso às seguintes informações vindas de um documento{}:
    
    ####
    {}
    ####
    Utilize as informações fornecidas para basear suas respostas.

    Sempre que houver $ na saída, substitua por S.

    Se a informação do documento for algo como "Just a moment...Enable JavaScript and coockies to continue", sugira ao usuário carregar novamente de JúrIA!
    '''.format(tipo_arquivo, documento)
    template = ChatPromptTemplate.from_messages([
        ('system', system_message),
        ('placeholder', '{chat_history}'),
        ('user', '{input}')
    ])

    chat = CONFIG_MODELOS[provedor]['chat'](model=modelo, api_key=api_key)
    chain = template | chat
    st.session_state['chain'] = chain
    


def pagina_chat():
    st.header('⚖️ JúrIA - Assistente Virtual do CAOJÚRI')

    # Verificar se há transcrições para exibir opções de download
    chaves_transcrição = [k for k in st.session_state.keys() if k.startswith('mostrar_download_')]
    if chaves_transcrição:
        st.subheader("Transcrições Disponíveis para Download")
        for chave in chaves_transcrição:
            nome_arquivo_base = chave.replace('mostrar_download_', '')
            if st.session_state.get(chave, False):
                transcricao = st.session_state.get(f'transcricao_{nome_arquivo_base}', '')
                duracao = st.session_state.get(f'duracao_{nome_arquivo_base}', 0)
                mostrar_opcoes_download(nome_arquivo_base, transcricao, duracao)
        
        st.divider()

    chain = st.session_state.get('chain')
    if chain is None:
        st.error('⚠️ Carregue o arquivo ou digite a url antes de inicializar a JúrIA!')
        st.stop()

    memoria = st.session_state.get('memoria', MEMORIA)
    for mensagem in memoria.buffer_as_messages:
        chat = st.chat_message(mensagem.type)
        chat.markdown(mensagem.content)

    input_usuario = st.chat_input('Fale com o Assistente!')
    if input_usuario:
        memoria.chat_memory.add_user_message(input_usuario)
        chat = st.chat_message('human')
        chat.markdown(input_usuario)

        chat = st.chat_message('ai')
        resposta = chat.write_stream(chain.stream({
            'input': input_usuario,
            'chat_history': memoria.buffer_as_messages
            }))
        #resposta = chat_model.invoke(input_usuario).content
        memoria.chat_memory.add_ai_message(resposta)
        st.session_state['memoria'] = memoria
        #st._rerun()
        
def sidebar():
    tabs_assistente = st.tabs(['Modelo de IA','RAG de dados'])
    
    with tabs_assistente[0]:
        provedor = st.selectbox('Selecione a empresa criadora do modelo de IA', CONFIG_MODELOS.keys())
        modelo = st.selectbox('Selecione o modelo de IA', CONFIG_MODELOS[provedor]['modelos'])
        api_key = st.text_input(
            f'Adicione a API do modelo escolhido: {provedor}',
            value=st.session_state.get(f'api_key_{provedor}')
        )
        st.session_state[f'api_key_{provedor}'] = api_key

        # Adiciona a mensagem condicional
        if api_key:
            st.info('API adicionada! Agora vá para o menu "RAG de dados" para iniciar o assistente.')


    with tabs_assistente[1]:
        tipo_arquivo = st.selectbox('selecione o tipo de URL ou arquivo', TIPOS_ARQUIVOS)
        if tipo_arquivo == 'Site':
            arquivo = st.text_input('Digite a URL do site')
        elif tipo_arquivo == 'Youtube':
            arquivo = st.text_input('Digite a URL do Youtube')
        elif tipo_arquivo == 'Google Drive':
            arquivo = st.text_input('Digite a URL do arquivo no Google Drive')
        elif tipo_arquivo == 'Arquivos .pdf':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .pdf', type=['.pdf'], accept_multiple_files=True)
        elif tipo_arquivo == 'Arquivos .csv':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .csv', type=['.csv'], accept_multiple_files=True)
        elif tipo_arquivo == 'Arquivos .txt':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .txt', type=['.txt'], accept_multiple_files=True)
        elif tipo_arquivo == 'Arquivos .mp4':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .mp4', type=['mp4'], accept_multiple_files=True)
            st.info('Os arquivos MP4 serão processados para extrair e transcrever o áudio. Após o processamento, você poderá baixar a transcrição em formato .txt ou .srt (legendas).')

    #with tabs_assistente[2]:
        #tipo_arquivo = st.selectbox('selecione o tipo o Notion', ARQUIVO_NOTION)
        if tipo_arquivo == 'Notion':
            use_env_page = st.checkbox("Usar ID da página configurado no .env", value=True)
            if use_env_page:
                notion_page_id = os.getenv('NOTION_PAGE_ID')
                if notion_page_id:
                    st.success("Usando ID da página do Notion")
                    arquivo = notion_page_id  # Will use the .env value
                else:
                    st.warning("ID da página do Notion não configurado no arquivo .env")
                    arquivo = st.text_input('Digite o ID da página do Notion')
            else:
                arquivo = st.text_input('Digite o ID da página do Notion')

            st.info("""
            As configurações do Notion estão sendo carregadas.
            
            
            """)
            
            notion_api_key = os.getenv('NOTION_API_KEY')
            notion_page_id = os.getenv('NOTION_PAGE_ID')
            
            notion_api_status = "✅ Configurada" if notion_api_key else "❌ Não encontrada"
            notion_page_status = "✅ Configurada" if notion_page_id else "❌ Não encontrada"
            
            st.write(f"Status da API Notion: {notion_api_status}")
            st.write(f"Status da Página Notion: {notion_page_status}")
            
            if notion_page_id:
                st.success("ID da Página Notion configurada")
                st.checkbox("Usar página configurada no .env", key="use_env_page_id", value=True)
            else:
                st.warning("ID da Página Notion não configurada no arquivo .env")
                st.text_input("Digite o ID da página do Notion (opcional)", key="manual_notion_page_id")
            
            st.link_button('Criar Nova Integração no Notion', 'https://www.notion.so/my-integrations')  


        if st.button('▶️ Iniciar o Assistente', use_container_width=True):
            carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo)

        if st.button('🗑️ Limpar o histórico de conversação', use_container_width=True):
            st.session_state['memoria'] = MEMORIA

def main():
    
    with st.sidebar:
        sidebar()
    pagina_chat()
if __name__=='__main__':
    main()