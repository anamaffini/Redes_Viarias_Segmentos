# Redes Viárias OSMnx por Município 
### QGIS Processing Algorithm

Este repositório contém um algoritmo de processamento para o QGIS que baixa redes viárias do OpenStreetMap usando o **OSMnx**, a partir de **um ou vários códigos de município do IBGE**, e salva os **segmentos de rede (edges)** em **um único arquivo GeoPackage**, com **uma camada por município**.

O script foi desenvolvido para facilitar análises urbanas, morfológicas e de mobilidade, integrando fluxos de trabalho em Python (OSMnx, GeoPandas) diretamente na interface gráfica do QGIS.

> **Autores**:  
> Gustavo Maciel Gonçalves (ORCID: 0000-0001-6726-4711)  
> Ana Luisa Maffini (ORCID: 0000-0001-5334-7073)  
> Contato: `analuisamaffini@gmail.com`
>
> To cite: Maffini, A. L., & Gonçalves, G. (2025). Redes Viarias Segmentos (Versão v01). Zenodo. https://doi.org/10.5281/zenodo.17630539

---

## Última Atualização

### Versão 02
Data: 11-06-2026

- O que mudou?
  - O script agora identifica se as bibliotecas python necessárias estão instaladas, e
  caso não esteja ele tenta instalar automaticamente.


## 🎯 Principais funcionalidades

- Baixa redes viárias do **OpenStreetMap** via **OSMnx** para um ou mais municípios brasileiros.
- Entrada por **código IBGE** (6 ou 7 dígitos), com suporte a:
  - um único código; ou  
  - vários códigos separados por vírgula, ponto e vírgula, espaço ou quebra de linha.
- Suporte a diferentes tipos de rede OSMnx:
  - `drive`, `all`, `walk`, `bike`, `drive_service`.
- Aplicação de **buffer em metros** ao redor do limite municipal antes de baixar a rede.
- Salva todos os municípios em **um único GeoPackage (`.gpkg`)**, com:
  - **uma camada por município**, nomeada como `osm_segments_<CODIGOIBGE>`.
- Adiciona automaticamente as camadas resultantes ao projeto QGIS, com nomes legíveis contendo município, UF, tipo de rede e buffer (quando houver).
- Tratamento de problemas comuns de **CRS/PROJ** em ambientes Windows (remoção do CRS antes de salvar, para evitar erros de escrita).

---

## 🧱 Arquivo principal

- `osmnx_municipio_segmentos.py`  
  Script Python que implementa o algoritmo de processamento do QGIS, incluindo:
  - definição de parâmetros de entrada/saída;
  - consulta à API de localidades do IBGE;
  - uso do OSMnx para busca do limite municipal e da rede viária;
  - aplicação de buffer opcional;
  - projeção da rede para CRS métrico;
  - exportação para GeoPackage com múltiplas camadas;
  - carregamento automático no projeto QGIS. :contentReference[oaicite:1]{index=1}  

---

## ✅ Requisitos

### Software

- **QGIS 3.22+** (recomendado)
- Python embutido no QGIS (ambiente padrão do QGIS)

### Bibliotecas Python (no ambiente do QGIS)

As bibliotecas abaixo precisam estar instaladas **no mesmo Python que o QGIS usa**:

- `osmnx`
- `geopandas`
- `requests`
- `shapely`
- `pyproj`

A instalação dessas bibliotecas varia conforme o sistema operacional e a forma como o QGIS foi instalado. Em geral, recomenda-se:

- usar o **OSGeo4W Shell** (Windows) ou
- configurar um ambiente virtual Python apontando para o QGIS.

---

## 🔧 Instalação do script no QGIS

1. Abra o QGIS.
2. Vá em **Processamento → Caixa de Ferramentas**.
3. No menu de scripts (ícone de roldana / ⋮), escolha **“Adicionar script...”**.
4. Selecione o arquivo `osmnx_municipio_segmentos.py`.
5. Após carregar, o algoritmo aparecerá em:

OSM / Redes Segmentos
└── Redes Viárias - Segmentos

---

## ▶️ Como usar

1. Abra a **Caixa de Ferramentas** no QGIS.
2. Procure por **“Redes Viárias - Segmentos”** (grupo: *OSM / Redes Segmentos*).
3. Preencha os parâmetros:

- **Código(s) do município (IBGE)**  
  - Exemplo (um município): `4314902`  
  - Exemplo (vários municípios):  
    - `4314902, 4305108, 4323002`  
    - ou `4314902;4305108;4323002`  
    - ou uma lista com quebras de linha.
- **Tipo de rede (OSMnx)**  
  - `drive`, `all`, `walk`, `bike`, `drive_service`.
- **Buffer ao redor do município (m)**  
  - `0` para usar apenas o limite municipal.
  - Ex: `1000` para incluir um buffer de 1 km ao redor.
- **Arquivo de saída (GeoPackage)**  
  - Escolha um caminho, por exemplo:  
    `C:/dados/redes_viarias.gpkg`

4. Clique em **Executar**.

### O que o algoritmo faz

- Para cada código IBGE informado:
- consulta a **API do IBGE** para obter nome do município e UF;
- usa o **OSMnx** para:
 - obter o polígono do município;
 - aplicar o buffer (se houver);
 - baixar a rede viária para o tipo de rede escolhido;
 - projetar a rede para UTM;
 - converter o grafo em GeoDataFrames (nodes/edges).
- exporta a camada de **segmentos (edges)** para o GeoPackage:
 - arquivo: o mesmo `.gpkg` para todos os municípios;
 - nome da camada: `osm_segments_<CODIGOIBGE>`.
- adiciona a camada ao projeto QGIS com um nome amigável:
 - exemplo: `OSMnx_Porto_Alegre_RS_drive_segments_buf1000m`.

---

## 📁 Estrutura de saída

- **Arquivo**: único GeoPackage, por exemplo:
- `redes_viarias.gpkg`
- **Camadas** dentro do GPKG:
- `osm_segments_4314902`
- `osm_segments_4305108`
- `osm_segments_4323002`
- **Camadas carregadas no QGIS**:
- `OSMnx_Porto_Alegre_RS_drive_segments`
- `OSMnx_Porto_Alegre_RS_drive_segments_buf1000m`
- etc.

---

## ⚠️ Observações importantes

- Mesmo que você selecione **Shapefile** na saída, o script **forçará a extensão `.gpkg`**, pois o formato Shapefile não suporta múltiplas camadas em um único arquivo.
- Em alguns ambientes, o CRS dos dados pode não ser reconhecido automaticamente ao salvar:
- o script **remove o CRS** antes de exportar para evitar erros de PROJ/Fiona;
- depois, você pode **definir manualmente o SRC** correto no QGIS (tipicamente a projeção UTM escolhida automaticamente pelo OSMnx).
- A execução pode demorar em:
- municípios muito extensos;
- redes muito densas;
- buffers grandes;
- conexões lentas com servidores do OSM.

---

## 🧪 Exemplos de uso

### Exemplo 1 — Um único município, sem buffer

- Códigos IBGE: `4314902`
- Tipo de rede: `drive`
- Buffer: `0`
- Saída: `C:/dados/poa_drive.gpkg`

Resultado:  
Uma camada de segmentos para Porto Alegre (drive), em um GPKG.

### Exemplo 2 — Vários municípios, com buffer

- Códigos IBGE: `4314902,4305108`
- Tipo de rede: `all`
- Buffer: `1000`
- Saída: `C:/dados/redes_metropolitanas.gpkg`

Resultado:  
Camadas `osm_segments_4314902` e `osm_segments_4305108` no mesmo GPKG, ambas com buffer de 1 km ao redor dos limites municipais.

---

## 📚 Referências

- Boeing, G. (2017). *OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks*. Computers, Environment and Urban Systems, 65, 126–139.  
- OSMnx: <https://github.com/gboeing/osmnx>  
- QGIS: <https://qgis.org>  
- OpenStreetMap: <https://www.openstreetmap.org>  
- API de Localidades IBGE: <https://servicodados.ibge.gov.br/api/docs/localidades>  

---
