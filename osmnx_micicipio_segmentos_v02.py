# -*- coding: utf-8 -*-
"""
Algoritmo de processamento para QGIS:
Baixa rede viária do OpenStreetMap com OSMnx, a partir
do(s) código(s) de município do IBGE, e salva a rede de segmentos.

Versão com verificação e tentativa de instalação automática de bibliotecas.

Autores: Gustavo Maciel Gonçalves (ORCID: 0000-0001-6726-4711), Ana Luisa Maffini (ORCID: 0000-0001-5334-7073)
Contato: analuisamaffini@gmail.com

Data da última atualização: 11-06-2026
Data de criação: 17-11-2025
"""

"""
Importações de Bibliotecas
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

import os
import sys
import json
import subprocess
import importlib


def ensure_package(package_name, import_name=None, feedback=None):
    """
    Verifica se uma biblioteca está instalada no Python do QGIS.
    Caso não esteja, tenta instalar automaticamente usando pip.
    """

    import_name = import_name or package_name

    try:
        return importlib.import_module(import_name)

    except ImportError:

        if feedback:
            feedback.pushInfo(
                f"Biblioteca '{package_name}' não encontrada. Tentando instalar automaticamente..."
            )

        try:
            subprocess.check_call([
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                package_name
            ])

            if feedback:
                feedback.pushInfo(
                    f"Biblioteca '{package_name}' instalada com sucesso."
                )

            return importlib.import_module(import_name)

        except Exception as e:
            raise QgsProcessingException(
                f"A biblioteca '{package_name}' não está instalada "
                f"e a instalação automática falhou.\n\n"
                f"Instale manualmente no ambiente Python do QGIS.\n\n"
                f"Erro: {e}"
            )


class OSMnxMunicipioSegments(QgsProcessingAlgorithm):
    """
    Baixar rede viária OSMnx por município, aceitando mais de um código
    e salvando tudo em um único GeoPackage, com uma camada por município.
    """

    PARAM_MUN_CODE = "MUNICIPIO_IBGE"
    PARAM_OUTPUT = "OUTPUT"
    PARAM_NET_TYPE = "NETWORK_TYPE"
    PARAM_BUFFER_M = "BUFFER_METERS"

    NET_TYPE_OPTIONS = ["drive", "all", "walk", "bike", "drive_service"]

    def tr(self, text):
        return QCoreApplication.translate("OSMnxMunicipioSegments", text)

    def createInstance(self):
        return OSMnxMunicipioSegments()

    def name(self):
        return "osmnx_municipio_segments"

    def displayName(self):
        return self.tr("Redes Viárias - Segmentos")

    def group(self):
        return self.tr("OSM / Redes Segmentos")

    def groupId(self):
        return "osmnx_networks"

    def shortHelpString(self):
        return self.tr(
            "Baixa a rede viária de um ou mais municípios brasileiros a partir "
            "do(s) código(s) IBGE, usando OSMnx, projeta a rede e salva os "
            "segmentos em um único GeoPackage, com uma camada por município.\n\n"
            "O algoritmo verifica se as bibliotecas necessárias estão instaladas. "
            "Caso não estejam, tenta instalá-las automaticamente no Python do QGIS.\n\n"
            "Bibliotecas verificadas:\n"
            " - requests\n"
            " - geopandas\n"
            " - osmnx\n\n"
            "Observação: a instalação automática pode falhar em alguns ambientes "
            "do QGIS, especialmente no Windows, por causa de dependências compiladas."
        )

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterString(
                self.PARAM_MUN_CODE,
                self.tr(
                    "Código(s) do município IBGE. "
                    "Para vários municípios, separe por vírgula, ponto e vírgula ou espaço."
                )
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PARAM_NET_TYPE,
                self.tr("Tipo de rede OSMnx"),
                self.NET_TYPE_OPTIONS,
                defaultValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.PARAM_BUFFER_M,
                self.tr("Buffer ao redor do município, em metros"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.PARAM_OUTPUT,
                self.tr("Arquivo de saída GeoPackage"),
                self.tr("GeoPackage (*.gpkg);;Shapefile (*.shp)")
            )
        )

    def _parse_municipality_codes(self, mun_codes_str):
        """
        Converte a string digitada pelo usuário em uma lista de códigos IBGE.
        Aceita vírgula, ponto e vírgula, espaço e quebra de linha.
        """

        if not mun_codes_str:
            return []

        for sep in [";", "\n", "\t", " "]:
            mun_codes_str = mun_codes_str.replace(sep, ",")

        parts = mun_codes_str.split(",")

        codes = []

        for part in parts:
            code = "".join(c for c in part if c.isdigit())
            if code:
                codes.append(code)

        seen = set()
        unique_codes = []

        for c in codes:
            if c not in seen:
                seen.add(c)
                unique_codes.append(c)

        return unique_codes

    def processAlgorithm(self, parameters, context, feedback):

        # ==========================================================
        # 1. VERIFICAR E INSTALAR BIBLIOTECAS NECESSÁRIAS
        # ==========================================================

        feedback.pushInfo("Verificando bibliotecas Python necessárias...")

        requests = ensure_package("requests", "requests", feedback)
        gpd = ensure_package("geopandas", "geopandas", feedback)
        ox = ensure_package("osmnx", "osmnx", feedback)

        feedback.pushInfo("Bibliotecas verificadas com sucesso.")

        # ==========================================================
        # 2. LER PARÂMETROS
        # ==========================================================

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

        if net_type_index < 0 or net_type_index >= len(self.NET_TYPE_OPTIONS):
            net_type_index = 0

        network_type = self.NET_TYPE_OPTIONS[net_type_index]

        codes = self._parse_municipality_codes(mun_codes_str)

        if not codes:
            raise QgsProcessingException(
                self.tr("Informe ao menos um código de município do IBGE.")
            )

        feedback.pushInfo(
            self.tr(f"Códigos de município identificados: {', '.join(codes)}")
        )

        for code in codes:
            if len(code) not in (6, 7):
                feedback.reportError(
                    self.tr(
                        "Código IBGE geralmente possui 7 dígitos. "
                        f"Código informado: {code}"
                    )
                )

        # ==========================================================
        # 3. AJUSTAR SAÍDA PARA GEOPACKAGE
        # ==========================================================

        base, ext = os.path.splitext(out_path_user)

        if not ext:
            ext = ".gpkg"

        if ext.lower() == ".shp":
            feedback.reportError(
                self.tr(
                    "Foi selecionado Shapefile, mas o algoritmo salvará em GeoPackage "
                    "para permitir múltiplas camadas."
                )
            )
            ext = ".gpkg"

        if ext.lower() != ".gpkg":
            feedback.pushInfo(
                self.tr(
                    "Somente GeoPackage é plenamente compatível com múltiplas camadas. "
                    "A extensão foi ajustada para .gpkg."
                )
            )
            ext = ".gpkg"

        out_path = base + ext

        feedback.pushInfo(
            self.tr(f"GeoPackage de saída: {out_path}")
        )

        # ==========================================================
        # 4. CONFIGURAÇÕES DO OSMNX
        # ==========================================================

        ox.settings.use_cache = True
        ox.settings.log_console = False

        created_layers = []

        # ==========================================================
        # 5. PROCESSAR CADA MUNICÍPIO
        # ==========================================================

        for idx, mun_code in enumerate(codes, start=1):

            feedback.pushInfo(
                self.tr(
                    f"Processando município {idx}/{len(codes)} - código IBGE: {mun_code}"
                )
            )

            # ------------------------------------------------------
            # Consultar API do IBGE
            # ------------------------------------------------------

            url = (
                "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/"
                f"{mun_code}"
            )

            feedback.pushInfo(self.tr(f"Consultando IBGE: {url}"))

            try:
                r = requests.get(url, timeout=30)

            except Exception as e:
                raise QgsProcessingException(
                    self.tr(f"Erro ao conectar com a API do IBGE: {e}")
                )

            if r.status_code != 200:
                raise QgsProcessingException(
                    self.tr(
                        f"Erro ao consultar IBGE. Status {r.status_code}. "
                        f"Verifique o código do município: {mun_code}."
                    )
                )

            try:
                data = r.json()

            except json.JSONDecodeError:
                raise QgsProcessingException(
                    self.tr("Resposta da API do IBGE não é um JSON válido.")
                )

            if isinstance(data, list):
                if not data:
                    raise QgsProcessingException(
                        self.tr(
                            f"Nenhum município retornado pelo IBGE para o código {mun_code}."
                        )
                    )
                data = data[0]

            try:
                nome_mun = data["nome"]
                uf_sigla = data["microrregiao"]["mesorregiao"]["UF"]["sigla"]

            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        f"Não foi possível interpretar a resposta da API do IBGE "
                        f"para o código {mun_code}. Erro: {e}"
                    )
                )

            place_query = f"{nome_mun}, {uf_sigla}, Brasil"

            feedback.pushInfo(
                self.tr(
                    f"Município identificado: {nome_mun} - {uf_sigla}"
                )
            )

            feedback.pushInfo(
                self.tr(
                    f"Consulta OSMnx: {place_query}"
                )
            )

            feedback.pushInfo(
                self.tr(
                    f"Tipo de rede selecionado: {network_type}"
                )
            )

            if buffer_m and buffer_m > 0:
                feedback.pushInfo(
                    self.tr(
                        f"Buffer solicitado: {buffer_m} m."
                    )
                )
            else:
                feedback.pushInfo(
                    self.tr("Nenhum buffer adicional será aplicado.")
                )

            # ------------------------------------------------------
            # Obter limite municipal
            # ------------------------------------------------------

            try:
                place_gdf = ox.geocode_to_gdf(place_query)

            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        f"Erro ao obter o limite municipal com OSMnx para "
                        f"'{place_query}': {e}"
                    )
                )

            if place_gdf.empty:
                raise QgsProcessingException(
                    self.tr(
                        f"Não foi possível obter o limite municipal de '{place_query}'."
                    )
                )

            geom = place_gdf.geometry.iloc[0]

            # ------------------------------------------------------
            # Aplicar buffer, se solicitado
            # ------------------------------------------------------

            if buffer_m and buffer_m > 0:

                try:
                    try:
                        from osmnx.projection import project_gdf

                        place_proj = project_gdf(place_gdf)
                        place_proj["geometry"] = place_proj.buffer(buffer_m)
                        place_buff = place_proj.to_crs(epsg=4326)

                    except Exception:
                        place_proj = place_gdf.to_crs(epsg=3857)
                        place_proj["geometry"] = place_proj.buffer(buffer_m)
                        place_buff = place_proj.to_crs(epsg=4326)

                    geom = place_buff.geometry.iloc[0]

                except Exception as e:
                    feedback.reportError(
                        self.tr(
                            f"Erro ao aplicar buffer para '{place_query}'. "
                            f"Será usado apenas o limite municipal. Detalhes: {e}"
                        )
                    )

            # ------------------------------------------------------
            # Baixar rede viária
            # ------------------------------------------------------

            feedback.pushInfo(
                self.tr(
                    "Baixando rede viária do OpenStreetMap com OSMnx..."
                )
            )

            try:
                G = ox.graph_from_polygon(
                    geom,
                    network_type=network_type
                )

            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        f"Erro ao baixar rede com OSMnx para '{place_query}': {e}"
                    )
                )

            # ------------------------------------------------------
            # Projetar rede
            # ------------------------------------------------------

            try:
                G_proj = ox.project_graph(G)

            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        f"Erro ao projetar a rede para '{place_query}': {e}"
                    )
                )

            # ------------------------------------------------------
            # Converter grafo para GeoDataFrames
            # ------------------------------------------------------

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
                        f"Erro ao converter rede para GeoDataFrame em "
                        f"'{place_query}': {e}"
                    )
                )

            feedback.pushInfo(
                self.tr(
                    f"Segmentos obtidos para {nome_mun} - {uf_sigla}: {len(edges)}."
                )
            )

            # ------------------------------------------------------
            # Remover CRS antes de salvar, se necessário
            # ------------------------------------------------------

            try:
                if edges.crs is not None:
                    feedback.pushInfo(
                        self.tr(
                            f"Removendo CRS ({edges.crs}) antes de salvar "
                            "para evitar problemas de PROJ/CRS."
                        )
                    )
                    edges = edges.set_crs(None, allow_override=True)

            except Exception as e:
                feedback.reportError(
                    self.tr(
                        f"Não foi possível remover o CRS. Tentando salvar mesmo assim. "
                        f"Detalhes: {e}"
                    )
                )

            # ------------------------------------------------------
            # Salvar camada no GeoPackage
            # ------------------------------------------------------

            layer_name = f"osm_segments_{mun_code}"

            try:
                edges.to_file(
                    out_path,
                    layer=layer_name,
                    driver="GPKG"
                )

            except Exception as e:
                raise QgsProcessingException(
                    self.tr(
                        f"Erro ao salvar camada '{layer_name}' no GeoPackage: {e}"
                    )
                )

            created_layers.append(layer_name)

            # ------------------------------------------------------
            # Carregar camada no QGIS
            # ------------------------------------------------------

            uri = f"{out_path}|layername={layer_name}"

            vlayer_name = f"OSMnx_{nome_mun}_{uf_sigla}_{network_type}_segments"

            if buffer_m and buffer_m > 0:
                vlayer_name += f"_buf{int(buffer_m)}m"

            vlayer = QgsVectorLayer(
                uri,
                vlayer_name,
                "ogr"
            )

            if not vlayer.isValid():
                raise QgsProcessingException(
                    self.tr(
                        f"A camada '{layer_name}' foi criada, "
                        "mas não pôde ser carregada no QGIS."
                    )
                )

            context.temporaryLayerStore().addMapLayer(vlayer)
            QgsProject.instance().addMapLayer(vlayer)

            feedback.pushInfo(
                self.tr(
                    f"Camada adicionada ao projeto: {vlayer_name}\n"
                    f"GeoPackage: {out_path}\n"
                    f"Layer: {layer_name}"
                )
            )

        # ==========================================================
        # 6. FINALIZAÇÃO
        # ==========================================================

        if created_layers:
            feedback.pushInfo(
                self.tr(
                    "Camadas criadas no GeoPackage:\n  - "
                    + "\n  - ".join(created_layers)
                )
            )

        return {self.PARAM_OUTPUT: out_path}


# Fim do script