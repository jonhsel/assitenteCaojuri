import streamlit as st
import tempfile
from langchain.memory import ConversationBufferMemory

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_deepseek import ChatDeepSeek

from loaders import *
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


TIPOS_ARQUIVOS = ['Arquivos .pdf', 'Site', 'Youtube', 'Arquivos .csv', 'Arquivos .txt']

ARQUIVO_NOTION =['Notion']

CONFIG_MODELOS = {  'OpenAI': 
                            {'modelos': ['gpt-4o-mini', 'gpt-4o'],
                            'chat': ChatOpenAI},
                    'Anthropic':
                            {'modelos':['claude-3-5-haiku-20241022','claude-3-5-sonnet-20241022'],
                             'chat':ChatAnthropic},
                    'Google':
                            {'modelos':['gemini-2.0-flash', 'gemini-2.0-flash-lite-preview-02-05', 'gemini-1.5-flash', 'gemini-1.5-pro'],
                             'chat': ChatGoogleGenerativeAI},
                    'DeepSeek': {'modelos':['-'],'chat': ChatDeepSeek}
}

MEMORIA = ConversationBufferMemory()

def carrega_arquivo (tipo_arquivo, arquivo):
    documentos = []
    

    if tipo_arquivo == 'Site':
        documento = carrega_site(arquivo)  
        documentos.append(documento)  

    if tipo_arquivo == 'Youtube':
        documento = carrega_youtube(arquivo)
        documentos.append(documento)  

    elif tipo_arquivo in ['Arquivos .pdf', 'Arquivos .csv', 'Arquivos .txt']:
        for arq in arquivo: # Itera sobre a lista de arquivos
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
    

    system_message = ''' Você é um assistente técnico chamado 'Assistente Virtual do CAOJÚRI'.
    Você possui acesso às seguintes informações vindas de um documento{}:
    
    ####
    {}
    ####
    Utilize as informações fornecidas para basear suas respostas.

    Sempre que houver $ na saída, substitua por S.

    Se a informação do documento for algo como "Just a moment...Enable JavaScript and coockies to continue", sugira ao usuário carregar novamente o 'Assistente do Jonh Selmo'!
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
    st.header('⚖️ Assistente Virtual - CAOJÚRI')

    chain = st.session_state.get('chain')
    if chain is None:
        st.error('⚠️ Carregue o arquivo ou digite a url/id antes de inicializar o assistente!')
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
    tabs_assistente = st.tabs(['Modelo de IA','Uploads de Arquivos', 'Notion'])
    
    with tabs_assistente[0]:
        provedor = st.selectbox('Selecione a empresa criadora do modelo de IA', CONFIG_MODELOS.keys())
        modelo = st.selectbox('Selecione o modelo de IA', CONFIG_MODELOS[provedor]['modelos'])
        api_key = st.text_input(
            f'Adicione a API do modelo escolhido: {provedor}',
            value=st.session_state.get(f'api_key_{provedor}')
        )
        st.session_state[f'api_key_{provedor}'] = api_key

    with tabs_assistente[1]:
        tipo_arquivo = st.selectbox('selecione o tipo de URL ou arquivo', TIPOS_ARQUIVOS)
        if tipo_arquivo == 'Site':
            arquivo = st.text_input('Digite a URL do site')
        if tipo_arquivo == 'Youtube':
            arquivo = st.text_input('Digite o ID Youtube : Código alfanumérico situado entre "v=" e "&" da URL')
        if tipo_arquivo == 'Arquivos .pdf':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .pdf', type=['.pdf'], accept_multiple_files=True)
        if tipo_arquivo == 'Arquivos .csv':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .csv', type=['.csv'], accept_multiple_files=True)
        if tipo_arquivo == 'Arquivos .txt':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .txt', type=['.txt'], accept_multiple_files=True)
        
    with tabs_assistente[2]:
        tipo_arquivo = st.selectbox('selecione o tipo o Notion', ARQUIVO_NOTION)
        if tipo_arquivo == 'Notion':
            use_env_page = st.checkbox("Usar ID da página configurado no .env", value=True)
            if use_env_page:
                notion_page_id = os.getenv('NOTION_PAGE_ID')
                if notion_page_id:
                    st.success(f"Usando ID da página do Notion do arquivo .env: {notion_page_id}")
                    arquivo = None  # Will use the .env value
                else:
                    st.warning("ID da página do Notion não configurado no arquivo .env")
                    arquivo = st.text_input('Digite o ID da página do Notion')
            else:
                arquivo = st.text_input('Digite o ID da página do Notion')

        st.info("""
        As configurações do Notion estão sendo carregadas do arquivo .env
        
        Crie um arquivo .env na raiz do projeto com o seguinte conteúdo:
        ```
        NOTION_API_KEY=sua_chave_api_aqui
        NOTION_PAGE_ID=id_da_pagina_notion
        ```
        """)
        
        notion_api_key = os.getenv('NOTION_API_KEY')
        notion_page_id = os.getenv('NOTION_PAGE_ID')
        
        notion_api_status = "✅ Configurada" if notion_api_key else "❌ Não encontrada"
        notion_page_status = "✅ Configurada" if notion_page_id else "❌ Não encontrada"
        
        st.write(f"Status da API Notion: {notion_api_status}")
        st.write(f"Status da Página Notion: {notion_page_status}")
        
        if notion_page_id:
            st.success(f"ID da Página Notion configurada: {notion_page_id}")
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