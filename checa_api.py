import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def check_notion_api_limits(notion_client, database_id):
    try:
        # Faça uma requisição e capture os cabeçalhos
        response = notion_client.databases.query(
            database_id=database_id,
            page_size=1  # Requisição mínima
        )

        # Se a biblioteca não expõe diretamente, você pode precisar 
        # usar requests diretamente
        import requests

        headers = {
            'Authorization': f'Bearer {os.getenv("NOTION_API_KEY")}',
            'Notion-Version': '2022-06-28'  # Versão atual da API
        }

        response = requests.get(
            f'https://api.notion.com/v1/databases/{database_id}',
            headers=headers
        )

        # Imprimir limites de taxa
        print("Límites da API Notion:")
        print(f"Limite de Requisições: {response.headers.get('X-RateLimit-Limit')}")
        print(f"Requisições Restantes: {response.headers.get('X-RateLimit-Remaining')}")
        print(f"Tempo até Reset: {response.headers.get('X-RateLimit-Reset')}")

    except Exception as e:
        print(f"Erro ao verificar limites: {e}")
        return False

if __name__ == '__main__':
    # Inicialize o cliente Notion
    notion = Client(auth=os.getenv('NOTION_API_KEY'))

    # ID do banco de dados Notion
    database_id = os.getenv('NOTION_PAGE_ID')

    # Verifique os limites da API
    check_notion_api_limits(notion, database_id)