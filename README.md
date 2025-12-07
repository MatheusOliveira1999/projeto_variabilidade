# Variabilidade e Mudanças Climáticas (CMIP6)

Repositório para comparar projeções CMIP6 entre o período histórico e os cenários futuros SSP1-2.6 e SSP5-8.5 nas variáveis de vento e temperatura do ar na superfície, utilizando o modelo IPSL-CM6A-LR (France).

## Objetivo
- Baixar e organizar os dados CMIP6.
- Calcular sazonalidade mensal e anual, médias e anomalias em relação ao histórico.
- Comparar os cenários SSP1-2.6 (menos pessimista) e SSP5-8.5 (mais pessimista) para 2015–2049.

## Dados
- Período histórico: 1980–2014.
- Cenários futuros: 2015–2049 (SSP1-2.6 e SSP5-8.5).
- Variáveis: `near_surface_wind_speed` e `near_surface_air_temperature`.
- Modelo: `IPSL-CM6A-LR`.
- Área: `[N, W, S, E] = [0.25, -94.68, -23.09, -71.04]`.
- Resolução temporal: diária.

## Pré-requisitos
- Python 3.x com `pip`.
- Pacotes principais: `cdsapi` (para download). Para análise e gráficos, recomenda-se `xarray`, `pandas`, `matplotlib`/`plotly` e `scipy` (para estimar extremos de vento).
- Instale as dependências do projeto:
  ```bash
  python -m pip install -r requirements.txt
  ```

## Configuração da CDS API
1) Crie uma conta no Copernicus Climate Data Store e obtenha sua chave.
2) Crie o arquivo `~/.cdsapirc` com o conteúdo:
   ```
   url: https://cds.climate.copernicus.eu/api/v2
   key: <uid>:<token>
   ```
   Dica: crie o arquivo via terminal (troque `<uid>:<token>` pelo seu):
   ```bash
   cat > ~/.cdsapirc <<'EOF'
   url: https://cds.climate.copernicus.eu/api/v2
   key: <uid>:<token>
   EOF
   ```
   Se aparecer o erro `Missing/incomplete configuration file: ~/.cdsapirc`, refaça o passo acima.
3) Instale o pacote:
   ```bash
   python -m pip install cdsapi
   ```

## Download de dados (script `API.py`)
O `API.py` agora é configurável por linha de comando e já salva os arquivos em `date/historico` ou `date/projecao` conforme o experimento.

Exemplo (padrão: duas variáveis, histórico + SSP1-2.6 + SSP5-8.5):
```bash
python API.py
```

Exemplo alterando variável, área e período:
```bash
python API.py \
  --variables near_surface_air_temperature \
  --experiments historical ssp1_2_6 \
  --area 0.25 -94.68 -23.09 -71.04 \
  --historical-start 1980 --historical-end 2010 \
  --scenario-start 2015 --scenario-end 2040
```

Parâmetros principais:
- `--variables`: lista de variáveis do CDS (ex.: `near_surface_wind_speed`).
- `--experiments`: ex.: `historical`, `ssp1_2_6`, `ssp5_8_5`.
- `--area N W S E`: caixa de recorte.
- `--model`: modelo CMIP6 (padrão `ipsl_cm6a_lr`).
- `--historical-start/end` e `--scenario-start/end`: intervalos de anos.
- `--output-base`: diretório base (padrão `date`).
- Para rosa dos ventos, baixe também componentes u/v (ex.: `eastward_near_surface_wind` e `northward_near_surface_wind` ou `uas`/`vas`).

## Geração de gráficos (script `analysis.py`)
Lê os NetCDF baixados em `date/historico` e `date/projecao`, calcula climatologia, anomalias e séries anuais, e salva PNGs em `img/`.

Exemplo de uso:
```bash
python analysis.py --variable near_surface_air_temperature
```

Se os arquivos não seguirem o padrão de nome, informe manualmente:
```bash
python analysis.py \
  --variable near_surface_wind_speed \
  --historical-file date/historico/historical_near_surface_wind_speed_1980-2014_ipsl_cm6a_lr.nc \
  --scenario-file ssp1_2_6=date/projecao/ssp1_2_6_near_surface_wind_speed_2015-2049_ipsl_cm6a_lr.nc
```

Notas:
- Se a variável solicitada não estiver no arquivo, o script tenta aliases comuns (`near_surface_air_temperature` → `tas`; `near_surface_wind_speed` → `sfcWind`) ou usa a única variável de dados disponível.
- Para temperatura, se o arquivo estiver em Kelvin (`K`), o script converte para Celsius (`°C`) antes de gerar os gráficos.
- Gráficos gerados: climatologia mensal, anomalias mensais, série anual com médias (histórica e cenários), anomalias anuais vs. média histórica (não acumuladas), rosa dos ventos (se houver componentes u/v) e níveis de retorno de vento para períodos definidos (padrão: 10, 20, 50 anos).
- Rosa dos ventos depende de componentes u/v no NetCDF (ex.: `uas`/`vas`, `u10`/`v10`); se não existirem, o gráfico é ignorado.
- Para variáveis acumulativas (ex.: `total_precipitation`, `tp`, `pr`), as agregações mensais/anuais usam soma; para as demais, média. Eixos Y mostram o nome da variável com a unidade detectada.
- Parâmetro extra: `--return-periods` permite alterar os períodos de retorno (anos) usados no gráfico de extremos de vento.

## Etapas previstas de análise
- Construir a climatologia histórica (médias e sazonalidade mensal/anual) para cada variável.
- Calcular anomalias positivas/negativas para SSP1-2.6 e SSP5-8.5 em relação ao histórico.
- Gerar gráficos de sazonalidade e séries temporais com linhas das médias (histórica e de cada cenário) para acompanhar a evolução das variáveis.

## Estrutura do repositório
- `API.py`: script de download via CDS API.
- `analysis.py`: geração de climatologia, anomalias e gráficos.
- `README.md`: este guia do projeto.
