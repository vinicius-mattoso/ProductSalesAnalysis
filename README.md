# Product Sales Analysis

Projeto de analise de vendas de produtos com EDA, dashboard operacional,
forecasting de receita e clusterizacao ABC para priorizacao comercial.

O objetivo e transformar uma base transacional de vendas em uma visao pratica
para acompanhamento de performance, identificacao de produtos relevantes e apoio
a decisoes de estoque, campanhas e planejamento de receita.

## Visao geral

O projeto cobre quatro frentes principais:

1. **Analise exploratoria de dados (EDA)** para entender qualidade, volume,
   distribuicoes e concentracao das vendas.
2. **Dashboard de vendas** em FastAPI, HTML, CSS e JavaScript para monitoramento
   operacional.
3. **Forecasting de receita** para estimar os proximos 3 meses de vendas.
4. **Clusterizacao e classificacao ABC** para identificar produtos prioritarios.

## Base de dados

A base principal esta em:

```text
data/raw/product_sales_dataset.csv
```

Campos principais:

| Campo | Descricao |
|---|---|
| `Product_ID` | Identificador do produto/transacao |
| `Product_Name` | Nome do produto |
| `Category` | Categoria comercial |
| `Price_USD` | Preco unitario |
| `Quantity_Sold` | Quantidade vendida |
| `Total_Sales_USD` | Receita total da linha |
| `Order_Date` | Data da venda |
| `Customer_City` | Cidade do cliente |

A base possui 1.000 linhas, 24 produtos distintos e vendas entre janeiro de
2025 e maio de 2026.

## Dashboard

O dashboard fica em:

```text
dashboard_sales_app/
```

Ele entrega uma interface com filtros por categoria, cidade e produto, alem de:

- receita total;
- unidades vendidas;
- numero de pedidos;
- ticket medio;
- preco medio realizado;
- produto lider;
- categoria lider;
- cidade lider;
- tendencia mensal;
- momentum mensal;
- receita por categoria;
- receita por cidade;
- ranking de produtos;
- heatmap categoria x cidade.

## Como rodar localmente

Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependencias:

```powershell
pip install -r requirements.txt
```

Execute o dashboard:

```powershell
python dashboard_sales_app\main.py
```

Acesse:

```text
http://127.0.0.1:8001
```

## Analises do projeto

### 1. EDA

Notebook:

```text
notebooks/01_EDA.ipynb
```

A EDA avalia o periodo da base, consistencia entre preco, quantidade e receita,
categorias, produtos, cidades, comportamento mensal e concentracao de receita.

![Receita mensal observada](docs/assets/eda_monthly_sales.png)

![Receita por categoria e cidade](docs/assets/eda_segments.png)

### 2. Forecasting

Notebook:

```text
notebooks/02_forecasting_total_sales.ipynb
```

O forecasting estima a receita dos proximos 3 meses. Como maio de 2026 ainda
nao estava completo na base, o treino considera como ultimo mes completo abril
de 2026 e projeta maio, junho e julho de 2026.

Modelos avaliados:

- baseline naive;
- media movel de 3 meses;
- media movel de 6 meses;
- Exponential Smoothing;
- ARIMA via grid search;
- ARIMA/SARIMAX com drift;
- Random Forest Regressor;
- Gradient Boosting Regressor.

![Comparacao de modelos de forecasting](docs/assets/forecast_model_comparison.png)

![Forecast selecionado](docs/assets/forecast_selected.png)

### 3. Clusterizacao e ABC

Notebook:

```text
notebooks/03_clusterizacao_produtos_abc.ipynb
```

A clusterizacao cria uma visao de prioridade comercial por produto. Ela combina
receita, unidades, pedidos, preco medio, ticket medio, cidades atendidas, meses
ativos, crescimento recente, volatilidade e recencia da ultima venda.

![Top produtos por potencial comercial](docs/assets/cluster_top_products.png)

![Receita x unidades por classe ABC](docs/assets/cluster_revenue_units.png)

Classes geradas:

- `abc_revenue_class`: ABC tradicional baseado em receita historica.
- `abc_cluster_class`: classe derivada dos grupos do K-Means.
- `abc_potential_class`: classe final recomendada para negocio, baseada no
  `potential_score`.

## Estrutura do projeto

```text
ProductSalesAnalysis/
|
|-- data/
|   `-- raw/
|       `-- product_sales_dataset.csv
|
|-- dashboard_sales_app/
|   |-- main.py
|   |-- templates/
|   |   `-- index.html
|   `-- static/
|       |-- styles.css
|       `-- app.js
|
|-- docs/
|   `-- assets/
|       |-- eda_monthly_sales.png
|       |-- eda_segments.png
|       |-- forecast_model_comparison.png
|       |-- forecast_selected.png
|       |-- cluster_top_products.png
|       `-- cluster_revenue_units.png
|
|-- notebooks/
|   |-- 01_EDA.ipynb
|   |-- 02_forecasting_total_sales.ipynb
|   `-- 03_clusterizacao_produtos_abc.ipynb
|
|-- scripts/
|   `-- generate_readme_assets.py
|
|-- requirements.txt
`-- README.md
```

## Publicacao no GitHub Pages

GitHub Pages publica arquivos estaticos: HTML, CSS, JavaScript, imagens e JSON.
Ele nao executa uma aplicacao Python/FastAPI. Por isso, existem tres caminhos.

### Opcao 1: publicar este repositorio no GitHub Pages

Essa opcao cria uma URL do tipo:

```text
https://vinicius-mattoso.github.io/ProductSalesAnalysis/demos/productsalesanalysis/
```

Para isso, seria necessario gerar uma versao estatica do dashboard dentro da
pasta `docs/demos/productsalesanalysis/` ou em uma branch `gh-pages`, substituindo as
chamadas para `/api/dashboard` por dados JSON estaticos ou calculos feitos no
navegador.

Depois, no GitHub:

1. Abra o repositorio `ProductSalesAnalysis`.
2. Va em **Settings > Pages**.
3. Em **Build and deployment**, selecione **Deploy from a branch**.
4. Escolha a branch `main` e a pasta `/docs`.
5. Salve a configuracao.

### Opcao 2: publicar dentro do seu site `home`

Para usar uma URL como:

```text
https://vinicius-mattoso.github.io/home/demos/productsalesanalysis/
```

o conteudo estatico do dashboard precisa estar dentro do repositorio `home`,
por exemplo:

```text
home/
`-- demos/
    `-- productsalesanalysis/
        |-- index.html
        |-- assets/
        |   |-- styles.css
        |   |-- app.js
        |   `-- sales-data.json
```

Esse caminho e o mais adequado se o objetivo for manter um portfolio unico em
`/home/` e adicionar este projeto como uma pagina interna.

### Opcao 3: Pages + backend separado

Se quiser manter o dashboard exatamente como esta, com FastAPI servindo os
endpoints `/api/dashboard` e `/api/options`, o front pode ficar no GitHub Pages,
mas a API precisa rodar em outro servico, como Render, Railway, Fly.io ou uma
VPS. Nesse caso, o JavaScript do front passaria a buscar dados em uma URL
externa da API.

Para este projeto, a alternativa mais simples e gerar uma versao estatica para
o GitHub Pages, porque os dados estao em CSV local e podem ser pre-processados.

Para gerar essa versao estatica:

```powershell
python scripts\export_github_pages.py
```

O comando cria:

```text
docs/demos/productsalesanalysis/
|-- index.html
`-- assets/
    |-- app.js
    |-- styles.css
    `-- sales-data.json
```

Essa pasta pode ser publicada diretamente pelo GitHub Pages deste repositorio
ou copiada para uma pasta `demos/productsalesanalysis/` dentro do repositorio `home`.

Se quiser gerar direto para o repositorio `home`, use:

```powershell
python scripts\export_github_pages.py --out ..\home\demos\productsalesanalysis
```

Depois basta commitar e publicar o repositorio `home`.

## Proximos passos

- Gerar uma versao estatica do dashboard para GitHub Pages.
- Integrar o forecast ao dashboard.
- Integrar a classe `abc_potential_class` ao ranking de produtos.
- Criar forecast por categoria e por produto.
- Criar alertas de queda brusca de vendas.
- Estimar estoque minimo com base na demanda prevista.
