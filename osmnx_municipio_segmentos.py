# -*- coding: utf-8 -*-
"""
Algoritmo de processamento para QGIS:
Baixa rede viária do OpenStreetMap com OSMnx, a partir
do(s) código(s) de município do IBGE, e salva a rede de segmentos.

Versão: múltiplos municípios em UM ÚNICO GeoPackage,
com UMA CAMADA POR MUNICÍPIO (usando o parâmetro 'layer' do GeoPandas).

Autores: Gustavo Maciel Gonçalves (ORCID: 0000-0001-6726-4711), Ana Luisa Maffini (ORCID: 0000-0001-5334-7073)
Contato: analuisamaffini@gmail.com
Data: 17-11-2025
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingException,
    QgsVectorLayer,
    QgsProject
)

import requests
import json
import os


class OSMnxMunicipioSegments(QgsProcessingAlgorithm):
    """
    Baixar rede viária OSMnx por município (código IBGE),
    aceitando mais de um código e salvando tudo em um único GeoPackage,
    com uma camada por município.
    """

    PARAM_MUN_CODE = "MUNICIPIO_IBGE"
    PARAM_OUTPUT = "OUTPUT"
    PARAM_NET_TYPE = "NETWORK_TYPE"
    PARAM_BUFFER_M = "BUFFER_METERS"

    NET_TYPE_OPTIONS = ["drive", "all", "walk", "bike", "drive_service"]

    # ===== Métodos obrigatórios da API de Processamento do QGIS =====

    def tr(self, text):
        return QCoreApplication.translate("OSMnxMunicipioSegments", text)

    def createInstance(self):
        return OSMnxMunicipioSegments()

    def name(self):
        # identificador interno (sem espaços)
        return "osmnx_municipio_segments"

    def displayName(self):
        # nome que aparece na Caixa de Ferramentas
        return self.tr("Redes Viárias - Segmentos")

    def group(self):
        return self.tr("OSM / Redes Segmentos")

    def groupId(self):
        return "osmnx_networks"

    def shortHelpString(self):
        return self.tr(
            "Baixa a rede viária de um ou mais municípios brasileiros a partir "
            "do(s) código(s) IBGE, usando OSMnx, projeta a rede e salva os "
            "segmentos (edges) em UM ÚNICO GeoPackage, com UMA CAMADA POR MUNICÍPIO.\n\n"
            "Parâmetros principais:\n"
            " - Código(s) do município (IBGE): pode ser um código único ou "
            "   vários códigos separados por vírgula, ponto e vírgula ou espaço.\n"
            " - Tipo de rede (OSMnx): drive, all, walk, bike, drive_service\n"
            " - Buffer ao redor do município (m): distância em metros para "
            "   expandir o limite municipal antes de baixar a rede.\n\n"
            "Observação: mesmo que você escolha Shapefile na saída, o algoritmo "
            "converterá o caminho para GeoPackage para permitir múltiplas camadas."
        )

    def initAlgorithm(self, config=None):
        """
        Definição dos parâmetros de entrada/saída
        """

        # Código(s) IBGE do(s) município(s)
        self.addParameter(
            QgsProcessingParameterString(
                self.PARAM_MUN_CODE,
                self.tr(
                    "Código(s) do município (IBGE, 6 ou 7 dígitos). "
                    "Para vários municípios, separe por vírgula, ponto e vírgula ou espaço."
                )
            )
        )

        # Tipo de rede OSMnx (Enum)
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PARAM_NET_TYPE,
                self.tr("Tipo de rede (OSMnx)"),
                self.NET_TYPE_OPTIONS,   # opções em forma de lista
                defaultValue=0           # índice 0 -> "drive"
            )
        )

        # Buffer em metros
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PARAM_BUFFER_M,
                self.tr("Buffer ao redor do município (m)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0
            )
        )

        # Arquivo vetorial de saída
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.PARAM_OUTPUT,
                self.tr("Arquivo de saída (GeoPackage)"),
                self.tr("GeoPackage (*.gpkg);;Shapefile (*.shp)")
            )
        )

    def _parse_municipality_codes(self, mun_codes_str):
        """
        Converte a string digitada pelo usuário em uma lista de códigos IBGE
        (apenas dígitos), aceitando vírgula, ponto e vírgula, espaço e quebra de linha.
        """
        if not mun_codes_str:
            return []

        # Substituir separadores comuns por vírgula
        for sep in [";", "\n", "\t"]:
            mun_codes_str = mun_codes_str.replace(sep, ",")

        # Quebrar por vírgula
        parts = mun_codes_str.split(",")

        codes = []
        for part in parts:
            # manter apenas dígitos
            code = "".join(c for c in part if c.isdigit())
            if code:
                codes.append(code)

        # Remover duplicados mantendo a ordem
        seen = set()
        unique_codes = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                unique_codes.append(c)

        return unique_codes

    def processAlgorithm(self, parameters, context, feedback):
        """
        Lógica principal do algoritmo
        """
        # ----- Ler parâmetros -----
        mun_codes_str = self.parameterAsString(
            parameters,
            self.PARAM_MUN_CODE,
            context
        )

        out_path_user = self.parameterAsFileOutput(
            parameters,
            self.PARAM_OUTPUT,
            context
        )

        net_type_index = self.parameterAsEnum(
            parameters,
            self.PARAM_NET_TYPE,
            context
        )

        buffer_m = self.parameterAsDouble(
            parameters,
            self.PARAM_BUFFER_M,
            context
        )

        # Garantir índice válido
        if net_type_index < 0 or net_type_index >= len(self.NET_TYPE_OPTIONS):
            net_type_index = 0

        network_type = self.NET_TYPE_OPTIONS[net_type_index]

        # ----- Interpretar lista de códigos -----
        codes = self._parse_municipality_codes(mun_codes_str)

        if not codes:
            raise QgsProcessingException(
                self.tr("Informe ao menos um código de município do IBGE.")
            )

        feedback.pushInfo(
            self.tr(
                f"Códigos de município identificados: {', '.join(codes)}"
            )
        )

        # Aviso sobre tamanhos dos códigos
        for code in codes:
            if len(code) not in (6, 7):
                feedback.reportError(
                    self.tr(
                        "Código IBGE geralmente possui 7 dígitos "
                        "(alguns serviços usam 6). Código informado: {}"
                    ).format(code)
                )

        # ----- Ajustar para GeoPackage e avisar se o usuário escolheu SHP -----
        base, ext = os.path.splitext(out_path_user)
        if not ext:
            ext = ".gpkg"

        if ext.lower() == ".shp":
            feedback.reportError(
                self.tr(
                    "Foi selecionado Shapefile na saída, mas o algoritmo salvará "
                    "em GeoPackage para permitir múltiplas camadas. "
                    "O caminho será convertido para: '{}.gpkg'."
                ).format(base)
            )
            ext = ".gpkg"

        if ext.lower() != ".gpkg":
            feedback.pushInfo(
                self.tr(
                    "Somente GeoPackage (*.gpkg) é plenamente compatível com múltiplas camadas. "
                    "O caminho foi ajustado para extensão .gpkg."
                )
            )
            ext = ".gpkg"

        out_path = base + ext

        feedback.pushInfo(
            self.tr(f"GeoPackage de saída: {out_path}")
        )

        # ----- Importar OSMnx uma única vez -----
        try:
            import osmnx as ox
        except ImportError:
            raise QgsProcessingException(
                self.tr(
                    "O módulo 'osmnx' não está disponível no Python do QGIS.\n"
                    "Instale o OSMnx no ambiente Python que o QGIS utiliza "
                    "antes de rodar este algoritmo."
                )
            )

        # Configurações básicas do OSMnx
        ox.settings.use_cache = True
        ox.settings.log_console = False

        # Tentar importar GeoPandas uma única vez
        try:
            import geopandas as gpd  # noqa: F401
        except ImportError:
            raise QgsProcessingException(
                self.tr(
                    "O módulo 'geopandas' não está disponível no Python do QGIS.\n"
                    "Instale o GeoPandas no ambiente Python que o QGIS utiliza."
                )
            )

        created_layers = []

        # ===== Loop sobre cada município =====
        for idx, mun_code in enumerate(codes, start=1):
            feedback.pushInfo(
                self.tr(
                    f"Processando município {idx}/{len(codes)} - código IBGE: {mun_code}"
                )
            )

            # ----- Consultar API do IBGE para obter nome e UF do município -----
            url = (
                "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/"
                f"{mun_code}"
            )

            feedback.pushInfo(self.tr(f"Consultando IBGE: {url}"))

            try:
                r = requests.get(url, timeout=30)
            except Exception as e:
                raise QgsProcessingException(
                    self.tr("Erro ao conectar com a API do IBGE: {}").format(e)
                )

            if r.status_code != 200:
                raise QgsProcessingException(
                    self.tr(
                        "Erro ao consultar IBGE (status {}). "
                        "Verifique o código do município: {}."
                    ).format(r.status_code, mun_code)
                )

            try:
                data = r.json()
            except json.JSONDecodeError:
                raise QgsProcessingException(
                    self.tr("Resposta da API do IBGE não é um JSON válido.")
                )

            # A API pode retornar um objeto único ou uma lista
            if isinstance(data, list):
                if not data:
                    raise QgsProcessingException(
                        self.tr(
                            "Nenhum município retornado pelo IBGE para o código {}. "
                            "Verifique o código informado."
                        ).format(mun_code)
                    )
                data = data[0]

            try:
                nome_mun = data["nome"]
                uf_sigla = data["microrregiao"]["mesorregiao"]["UF"]["sigla"]
            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        "Não foi possível interpretar a resposta da API do IBGE "
                        "para o código {}. Estrutura inesperada: {}"
                    ).format(mun_code, e)
                )

            place_query = f"{nome_mun}, {uf_sigla}, Brasil"

            feedback.pushInfo(
                self.tr(
                    f"Município identificado: {nome_mun} - {uf_sigla} "
                    f"(consulta OSMnx: '{place_query}')"
                )
            )

            feedback.pushInfo(
                self.tr(f"Tipo de rede OSMnx selecionado: '{network_type}'")
            )

            if buffer_m and buffer_m > 0:
                feedback.pushInfo(
                    self.tr(
                        f"Buffer solicitado: {buffer_m} m ao redor do limite municipal."
                    )
                )
            else:
                feedback.pushInfo(
                    self.tr("Nenhum buffer adicional será aplicado (0 m).")
                )

            # ----- Obter polígono do município e aplicar buffer, se houver -----
            try:
                place_gdf = ox.geocode_to_gdf(place_query)
            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        "Erro ao obter o limite do município '{}' com OSMnx: {}"
                    ).format(place_query, e)
                )

            if place_gdf.empty:
                raise QgsProcessingException(
                    self.tr(
                        "Não foi possível obter o limite do município '{}' com OSMnx."
                    ).format(place_query)
                )

            geom = place_gdf.geometry.iloc[0]

            if buffer_m and buffer_m > 0:
                try:
                    # Projetar para um CRS métrico, aplicar buffer e voltar para WGS84
                    try:
                        from osmnx.projection import project_gdf
                        place_proj = project_gdf(place_gdf)
                        place_proj["geometry"] = place_proj.buffer(buffer_m)
                        place_buff = place_proj.to_crs(epsg=4326)
                    except Exception:
                        # Fallback: usar Web Mercator
                        place_proj = place_gdf.to_crs(epsg=3857)
                        place_proj["geometry"] = place_proj.buffer(buffer_m)
                        place_buff = place_proj.to_crs(epsg=4326)

                    geom = place_buff.geometry.iloc[0]
                except Exception as e:
                    feedback.reportError(
                        self.tr(
                            "Erro ao aplicar buffer para o município '{}'. "
                            "Usando apenas o limite municipal sem buffer. "
                            "Detalhes: {}"
                        ).format(place_query, e)
                    )

            # ----- Baixar e construir a rede viária -----
            feedback.pushInfo(
                self.tr(
                    "Baixando rede viária do OpenStreetMap com OSMnx "
                    "(pode demorar alguns instantes)..."
                )
            )

            try:
                # Usar o polígono (com ou sem buffer) para recorte
                G = ox.graph_from_polygon(geom, network_type=network_type)
            except Exception as e:
                raise QgsProcessingException(
                    self.tr("Erro ao baixar rede com OSMnx para '{}': {}").format(
                        place_query, e
                    )
                )

            # ----- Projetar a rede em UTM (métrico) -----
            try:
                G_proj = ox.project_graph(G)
            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        "Erro ao projetar a rede com OSMnx para '{}': {}"
                    ).format(place_query, e)
                )

            # Converter para GeoDataFrames (nodes e edges)
            try:
                nodes, edges = ox.graph_to_gdfs(
                    G_proj,
                    nodes=True,
                    edges=True,
                    fill_edge_geometry=True
                )
            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        "Erro ao converter rede para GeoDataFrame em '{}': {}"
                    ).format(place_query, e)
                )

            feedback.pushInfo(
                self.tr(
                    f"Segmentos (edges) obtidos para {nome_mun} - {uf_sigla}: "
                    f"{len(edges)}. Gravando em camada do GeoPackage..."
                )
            )

            # ----- Remover CRS antes de salvar, se necessário (workaround) -----
            try:
                if edges.crs is not None:
                    feedback.pushInfo(
                        self.tr(
                            f"Removendo CRS ({edges.crs}) antes de salvar para evitar "
                            "problemas de PROJ/CRS no ambiente. "
                            "Defina o SRC manualmente após o carregamento, se necessário."
                        )
                    )
                    edges = edges.set_crs(None, allow_override=True)
            except Exception as e:
                feedback.reportError(
                    self.tr(
                        "Não foi possível remover o CRS antes de salvar. "
                        "Tentando salvar mesmo assim. Detalhes: {}"
                    ).format(e)
                )

            # ----- Definir nome da camada dentro do GPKG -----
            # Ex: osm_segments_4305108
            layer_name = f"osm_segments_{mun_code}"

            # ----- Salvar como camada no GeoPackage único -----
            try:
                # driver explicitamente "GPKG"
                edges.to_file(out_path, layer=layer_name, driver="GPKG")
            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        "Erro ao salvar camada '{}' no GeoPackage: {}"
                    ).format(layer_name, e)
                )

            created_layers.append(layer_name)

            # ----- Carregar camada no projeto -----
            # Fonte de dados para GeoPackage + layer
            uri = f"{out_path}|layername={layer_name}"

            vlayer_name = f"OSMnx_{nome_mun}_{uf_sigla}_{network_type}_segments"
            if buffer_m and buffer_m > 0:
                vlayer_name += f"_buf{int(buffer_m)}m"

            vlayer = QgsVectorLayer(uri, vlayer_name, "ogr")

            if not vlayer.isValid():
                raise QgsProcessingException(
                    self.tr(
                        "Camada '{}' foi criada no GeoPackage, mas não pôde ser "
                        "carregada no QGIS."
                    ).format(layer_name)
                )

            context.temporaryLayerStore().addMapLayer(vlayer)
            QgsProject.instance().addMapLayer(vlayer)

            feedback.pushInfo(
                self.tr(
                    f"Camada '{vlayer_name}' adicionada ao projeto.\n"
                    f"GeoPackage: {out_path}\n"
                    f"Layer: {layer_name}"
                )
            )

        if created_layers:
            feedback.pushInfo(
                self.tr(
                    "Camadas criadas no GeoPackage:\n  - " +
                    "\n  - ".join(created_layers)
                )
            )

        return {self.PARAM_OUTPUT: out_path}


# Fim do script
