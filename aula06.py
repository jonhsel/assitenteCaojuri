import streamlit as st
from langchain.memory import ConversationBufferMemory

from langchain_openai import ChatOpenAI

from loaders import *


TIPOS_ARQUIVOS = ['Site', 'Youtube', 'pdf', 'csv', 'txt']

CONFIG_MODELOS = {  'OpenAI': 
                            {'modelos': ['gpt-4o-mini', 'gpt-4o'],
                            'chat': ChatOpenAI}


}

MEMORIA = ConversationBufferMemory()

def carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo):
    chat = CONFIG_MODELOS[provedor]['chat'](model=modelo, api_key=api_key)
    st.session_state['chat'] = chat


def pagina_chat():
    st.header('⚖️ Assistente do Jonh Selmo - CAOJÚRI')

    chat_model = st.session_state.get('chat')
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
        resposta = chat.write_stream(chat_model.stream(input_usuario))
        #resposta = chat_model.invoke(input_usuario).content
        memoria.chat_memory.add_ai_message(resposta)
        st.session_state['memoria'] = memoria
        #st._rerun()
        
def sidebar():
    tabs_assistente = st.tabs(['Uploads de Arquivos', 'Modelo de IA'])
    with tabs_assistente[0]:
        tipo_arquivo = st.selectbox('selecione o tipo de URL ou arquivo', TIPOS_ARQUIVOS)
        if tipo_arquivo == 'Site':
            arquivo = st.text_input('Digite a URL do site')
        if tipo_arquivo == 'Youtube':
            arquivo = st.text_input('Digite a URL do Youtube')
        if tipo_arquivo == 'pdf':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .pdf', type=['.pdf'])
        if tipo_arquivo == 'csv':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .csv', type=['.csv'])
        if tipo_arquivo == 'txt':
            arquivo = st.file_uploader('Carregue o arquivo do tipo .txt', type=['.txt'])
        
    with tabs_assistente[1]:
        provedor = st.selectbox('Selecione a empresa criadora do modelo de IA', CONFIG_MODELOS.keys())
        modelo = st.selectbox('Selecione o modelo de IA', CONFIG_MODELOS[provedor]['modelos'])
        api_key = st.text_input(
            f'Adicione a API do modelo escolhido{provedor}',
            value=st.session_state.get(f'api_key_{provedor}')
        )
        st.session_state[f'api_key_{provedor}'] = api_key


    if st.button('Iniciar o Assistente'):
        carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo)

def main():
    pagina_chat()
    with st.sidebar:
        sidebar()

if __name__=='__main__':
    main()