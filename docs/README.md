# Projeto extrator de dados

## Visão geral

O objetivo deste projeto é criar uma api capaz de extrair e armazenar dados provindos do site da embrapa, em particular 
do site com dados de [vitivinicultura](http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_01).

A arquitetura dessa solução irá consistir de:

* Api para gerenciar chamadas
* Airflow para gerenciar os job's, tasks e agendamentos
* MongoDB para armazenar os dados.

Abaixo um diagrama dessa arquitetura.

![](img/arquitetura.png)

## Casos de uso

O usuário terá basicamente 3 casos de uso:

### Iniciar job de scrappy

Esta primeira api deverá iniciar um job para baixar os dados, e deverá receber como parâmetro um range de anos; Parâmetros `yearStart` e `yearEnd`.

Com esses parâmetros iremos submeter o job no airflow, e deveremos retornar o status do job, se foi submetido com sucesso, e o id do job para posterior consulta.

### Consultar status do job de scrappy

Esta api deverá receber como path param o `jobId` do airflow; Deverá consultar o status deste job no airflow e retornar para o usuário.

### Extração de dados

A extração de dados consiste em 3 etapas:

* Extração 
* Transformação
* Persistência

Cada etapa será uma DAG construída no airflow.

## Diagramas de sequência

### Iniciar job de scrappy 

```mermaid
%%{init: {'theme': 'forest' } }%%

sequenceDiagram
  actor usuario as Usuário
  participant api as API
  participant airflow as Airflow
  
  usuario->>api: Solicita iniciar job de scrappy, informando ano inicial e final
  alt Se usuário informar corretamente ano inicial e final
    api->>airflow: Chama api do airflow passando os parâmetros do job `yearStart` e `yearEnd`
    alt Caso job tenha sido criado com sucesso
    airflow->>api: Retorna o Job ID
    api->>usuario: Retorna http status 201 e o job id
    else Senão
    airflow->>api: Retorna o motivo do erro
    api->>usuario: Retorna o erro 500 e o campo reason com o motivo do erro
    end
  else
    api->>usuario: Retorna status 400 e a mensagem de "ano inicial e final são obrigatórios!"
  end

```

---

### Consultar status do job


```mermaid
%%{init: {'theme': 'base'} }%%

sequenceDiagram

  actor usuario as Usuário
  participant api as API
  participant airflow as Airflow

  usuario->>api: Solicitar status do job, informando o job id como path param
  alt Se o usuário informar corretamente o job id
    api->>airflow: Consulta o status do job
    alt Se o job id for válido e existir
      airflow->>api: Retorna o status do job
      api->>usuario: Retorna o http status 200 e o status do job
    else
      airflow->>api: Retorna o erro 404
      api->>usuario: Retorna o erro 404 e o campo reason informando que o job não existe
    end
  else
    api->>usuario: Retornar o erro 400 e a mensagem de "job id é obrigatório!"
  end
```


### Extração de dados

```mermaid
%%{init: {'theme': 'default'} }%%
sequenceDiagram
  participant airflow as Airflow

  box rgba(245,217,154,255) Airflow 
  participant extract as DAG Extração
  participant transform as DAG Transformação
  participant persist as DAG Persistência
  end
  participant site as Site
  participant db as Mongo DB

  airflow-->>extract: Inicia o job<br/>(Assíncrono)

  loop Para cada ano do range informado
  extract->>site: Faz a requisição http para a página correspondente
  site->>extract: Retorna os dados brutos em html
  extract->>transform: Envia os dados brutos para o transform
  transform->>transform: Faz o parse dos dados em um formato de dicionário python
  transform->>persist: Envia os dados em dicionário
  persist->>persist: Transforma os dados em formato de mongo document
  persist->>db: Persiste os dados do documento
  end


```