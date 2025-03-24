
from langchain_community.document_loaders import (WebBaseLoader,
                                                  YoutubeLoader,
                                                  CSVLoader,
                                                  PyPDFLoader,
                                                  TextLoader
                                                  )


import os
from dotenv import load_dotenv
from notion_client import Client

#Load environment variables
load_dotenv()

def carrega_site(url):
    loader = WebBaseLoader(url)
    lista_documentos = loader.load()
    documento = '\n\n'.join([doc.page_content for doc in lista_documentos])
    return  documento


def carrega_youtube(video_id):
    loader = YoutubeLoader(video_id, add_video_info=False, language=['pt'])
    lista_documentos = loader.load()
    documento = '\n\n'.join([doc.page_content for doc in lista_documentos])
    return  documento 


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
        
