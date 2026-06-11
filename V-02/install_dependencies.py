# -*- coding: utf-8 -*-

"""
Instalador de dependências para o script OSMnx Município Segmentos.

Este script deve ser executado no QGIS.
"""

# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString
)

import sys
import subprocess
import importlib


class InstallDependencies(QgsProcessingAlgorithm):

    OUTPUT_MESSAGE = "OUTPUT_MESSAGE"

    def tr(self, text):
        return QCoreApplication.translate("InstallDependencies", text)

    def createInstance(self):
        return InstallDependencies()

    def name(self):
        return "install_osmnx_dependencies"

    def displayName(self):
        return self.tr("Instalar/Reparar Bibliotecas OSMnx")

    def group(self):
        return self.tr("OSM / Redes Segmentos")

    def groupId(self):
        return "osmnx_networks"

    def shortHelpString(self):
        return self.tr(
            "Instala ou repara as bibliotecas Python necessárias para o algoritmo "
            "de download de redes viárias com OSMnx."
        )

    def initAlgorithm(self, config=None):
        self.addOutput(
            QgsProcessingOutputString(
                self.OUTPUT_MESSAGE,
                self.tr("Mensagem")
            )
        )

    def show_info_box(self, title, message):
        QMessageBox.information(
            None,
            title,
            message
        )

    def show_error_box(self, title, message):
        QMessageBox.critical(
            None,
            title,
            message
        )

    def processAlgorithm(self, parameters, context, feedback):

        packages = [
            ("requests", "requests"),
            ("geopandas", "geopandas"),
            ("osmnx", "osmnx"),
        ]

        already_installed = []
        installed_or_repaired = []
        failed = []

        feedback.pushInfo("Verificando bibliotecas necessárias...")

        for package_name, import_name in packages:

            try:
                importlib.import_module(import_name)
                already_installed.append(package_name)
                feedback.pushInfo(f"OK: {package_name} já estava instalado.")
                continue

            except ImportError:
                feedback.pushInfo(
                    f"{package_name} não encontrado. Instalando/reparando..."
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

                importlib.import_module(import_name)
                installed_or_repaired.append(package_name)

                feedback.pushInfo(
                    f"OK: {package_name} instalado/reparado com sucesso."
                )

            except Exception as e:
                failed.append((package_name, str(e)))
                feedback.reportError(
                    f"Falha ao instalar/reparar {package_name}: {e}"
                )

        if failed:
            failed_text = "\n".join(
                [f"- {pkg}" for pkg, err in failed]
            )

            message = (
                "A instalação/reparo não foi concluída.\n\n"
                "As seguintes bibliotecas apresentaram erro:\n\n"
                f"{failed_text}\n\n"
                "Recomenda-se instalar manualmente pelo OSGeo4W Shell."
            )

            self.show_error_box(
                "Falha na instalação das bibliotecas",
                message
            )

            raise QgsProcessingException(message)

        if installed_or_repaired:
            installed_text = "\n".join(
                [f"- {pkg}" for pkg in installed_or_repaired]
            )

            if already_installed:
                already_text = "\n".join(
                    [f"- {pkg}" for pkg in already_installed]
                )
            else:
                already_text = "Nenhuma."

            message = (
                "Instalação/reparo concluído com sucesso.\n\n"
                "Bibliotecas instaladas ou reparadas:\n\n"
                f"{installed_text}\n\n"
                "Bibliotecas que já estavam instaladas:\n\n"
                f"{already_text}\n\n"
                "Reinicie o QGIS antes de executar o algoritmo principal."
            )

        else:
            already_text = "\n".join(
                [f"- {pkg}" for pkg in already_installed]
            )

            message = (
                "Todas as bibliotecas necessárias já estavam instaladas.\n\n"
                f"{already_text}\n\n"
                "Nenhuma instalação adicional foi necessária."
            )

        self.show_info_box(
            "Bibliotecas verificadas",
            message
        )

        feedback.pushInfo(message)

        return {
            self.OUTPUT_MESSAGE: message
        }