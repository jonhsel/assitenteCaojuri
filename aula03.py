import streamlit as st


MENSAGENS_EXEMLO = [
    ('user', 'Oi'),
    ('assistant', 'Tudo bem?'),
    ('user', 'Tudo ótimo!'),
    ('assistant', 'que excelente'),
]

def pagina_chat():
    st.header('⚖️ Assistente do Jonh Selmo - CAOJÚRI')

    mensagens = st.session_state.get('mensagens', [])
    for mensagem in mensagens:
        chat = st.chat_message(mensagem[0])
        chat.markdown(mensagem[1])

    input_usuario = st.chat_input('Fale com o Assistente!')
    if input_usuario:
        mensagens.append(('user', input_usuario))
        st.session_state['mensagens'] = mensagens
        st._rerun()
        

def main():
    pagina_chat()

if __name__=='__main__':
    main()