from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# Configurações da DAG
default_args = {
  'owner': 'airflow',
  'depends_on_past': False,
  'start_date': datetime(2024, 9, 30),
  'email_on_failure': False,
  'email_on_retry': False,
  'retries': 1,
  'retry_delay': timedelta(minutes=5),
}

# Inicializando a DAG
with DAG(
  'fetch_process_embrapa_data',
  default_args=default_args,
  description='DAG para coletar e processar dados do site da Embrapa',
  schedule_interval=None,
  catchup=False
) as dag:

  # Constantes globais
  TABS = {
    "produção": "opt_02",
    "processamento": "opt_03",
    "comercialização": "opt_04",
    "importação": "opt_05",
    "exportação": "opt_06",
    "publicação": "opt_07",
  }

  SUBOPTIONS = {
    "produção": None,
    "processamento": ["subopt_01", "subopt_02", "subopt_03", "subopt_04"],
    "comercialização": None,
    "importação": ["subopt_01", "subopt_02", "subopt_03", "subopt_04", "subopt_05"],
    "exportação": ["subopt_01", "subopt_02", "subopt_03", "subopt_04"],
    "publicação": None,
  }

  # Função para buscar o HTML do site da Embrapa
  def fetch_data_from_site(**context):
    dag_run = context['dag_run']

    # Pegando os parâmetros passados no momento da execução
    tab = dag_run.conf.get('tab', 'processamento')
    year = dag_run.conf.get('year', 2023)

    suboptions = SUBOPTIONS.get(tab) or [None]

    all_html_data = []

    for suboption in suboptions:
      base_url = f"http://vitibrasil.cnpuv.embrapa.br/index.php?opcao={TABS[tab]}&ano={year}"
      if suboption:
        base_url += f"&subopcao={suboption}"
      
      response = requests.get(base_url)
      response.raise_for_status()  # Lança erro se houver falha na requisição
      html_content = response.text
      all_html_data.append({'suboption': suboption, 'html': html_content})
    
    # Passa os dados coletados para a próxima task usando XCom
    return all_html_data

  # Função para processar o HTML bruto e extrair os dados da tabela
  def process_data(**context):
    all_html_data = context['ti'].xcom_pull(task_ids='fetch_data_from_site')
    all_values = []

    def parse_table_data(tbody, columns_count):
      """Extrai os dados da tabela com base no número de colunas."""
      data = []
      current_item = None

      for row in tbody.select('tr'):
        cols = [col.text.strip() for col in row.find_all('td')]

        if len(cols) == columns_count:
          if columns_count == 2:
            name, quantity = cols
            if 'tb_item' in [td['class'][0] for td in row.find_all('td')]:
              current_item = {"name": name, "total_quantity": quantity, "types": []}
              data.append(current_item)
            else:
              current_item['types'].append({"name": name, "quantity": quantity})
          elif columns_count == 3:
            country, quantity, value = cols
            data.append({"country": country, "quantity": quantity, "value": value})

      return data

    for html_data in all_html_data:
      soup = BeautifulSoup(html_data['html'], "lxml")
      title = soup.select_one('div.content_center > p.text_center').text.strip()

      table = soup.find('table', class_="tb_dados")
      tbody = table.select_one('tbody')
      
      columns_count = len(tbody.find('tr').find_all('td'))
      table_data = parse_table_data(tbody, columns_count)

      all_values.append({
        "title": title,
        "suboption": html_data['suboption'],
        "values": table_data
      })

    return all_values

  # Tarefa 1: Buscar dados do site
  fetch_data_task = PythonOperator(
    task_id='fetch_data_from_site',
    python_callable=fetch_data_from_site,
    provide_context=True
  )

  # Tarefa 2: Processar os dados
  process_data_task = PythonOperator(
    task_id='process_data',
    python_callable=process_data,
    provide_context=True
  )

  fetch_data_task >> process_data_task
