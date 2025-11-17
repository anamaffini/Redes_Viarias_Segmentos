---
title: "OSMnx Municipality Network Downloader for QGIS: Automated Street-Network Extraction for Brazilian Municipalities"
authors:
  - name: "Ana Luisa Maffini"
    affiliation: "1"
    orcid: "0000-0001-5334-7073"
  - name: "Gustavo Maciel Gonçalves"
    affiliation: "1"
    orcid: "0000-0001-6726-4711"
affiliations:
  - name: "Universidade Federal do Rio Grande do Sul"
    index: 1
date: "2025-11-17"
bibliography: paper.bib
---

# Summary

The *OSMnx Municipality Network Downloader for QGIS* is an open-source Python tool that automates the retrieval, projection, and preparation of OpenStreetMap (OSM) street-network data for any Brazilian municipality using its official IBGE code. Implemented as a QGIS Processing Algorithm, the tool integrates the OSMnx library directly into the QGIS graphical interface, enabling users to download, buffer, and save high-quality street-segment datasets without requiring Python scripting. The software supports multiple network types (drive, walk, bike, all, and drive_service), handles projection and CRS inconsistencies automatically, and exports the resulting network as a GeoPackage or Shapefile, which is then added directly to the user’s QGIS project.

By providing a seamless interface between OSMnx and QGIS, the tool greatly expands access to advanced street-network extraction workflows for users who rely primarily on GUI-based spatial analysis. This includes researchers and practitioners in urban planning, geography, architecture, environmental risk assessment, transportation studies, and spatial data science. The software contributes to reproducible, scalable, and accessible urban analytics, particularly in the Brazilian context where IBGE codes serve as standardized national geospatial identifiers.

# Statement of Need

Street networks are foundational to urban studies and spatial analysis. Their topology, geometry, and connectivity underpin research in urban morphology, transportation planning, walkability and accessibility modeling, environmental exposure analysis, and climate-risk assessment. OpenStreetMap provides a vast, global, community-curated dataset, but extracting usable street networks from OSM typically requires specialized workflows.

OSMnx has become a leading Python library for downloading and analyzing street networks programmatically [@boeing2017]. However, its use requires a functioning scientific Python environment, familiarity with scripting, and manual integration with GIS software. For many researchers and practitioners—particularly those working in municipal planning offices, environmental institutes, and universities using QGIS for teaching—this presents a significant barrier. These users often work almost exclusively within the QGIS graphical environment and may lack the technical infrastructure needed to configure OSMnx and its dependencies.

The Brazilian context strengthens the need for a tool of this nature. The IBGE (Instituto Brasileiro de Geografia e Estatística) provides a nationally standardized system of municipal identifiers used extensively across public policy, census data, planning instruments, and academic research. A QGIS tool that accepts a municipal IBGE code, retrieves its boundary, optionally buffers this boundary, and downloads the corresponding OSM street network fills a critical methodological gap. It allows researchers to rely on a consistent, authoritative identifier while benefiting from automated, reproducible data extraction workflows.

The *OSMnx Municipality Network Downloader for QGIS* directly addresses this need. It democratizes access to advanced OSMnx network extraction while maintaining methodological rigor and reproducibility. By eliminating the need for scripting, the tool enables a wider audience—students, urban-planning professionals, geographers, environmental analysts, and researchers—to integrate high-quality street-network data into their work.

# Functionality

The tool is implemented as a QGIS Processing Algorithm written in Python. After installation, it becomes available in the QGIS Processing Toolbox under the group **“OSM / Redes viárias”** as *“Baixar rede viária OSMnx por município (IBGE)”*. Users interact with the tool through four parameters:

1. **IBGE municipality code** (a 6- or 7-digit identifier).
2. **Network type** (drive, walk, bike, all, drive_service).
3. **Optional buffer distance** in meters.
4. **Output file path** (GeoPackage or Shapefile).

Once executed, the algorithm performs the following steps:

## 1. IBGE code validation and API lookup
The tool ensures the code contains only digits and has the correct length. It then queries the IBGE Localidades API [@ibge_localidades], retrieving the municipality name and state abbreviation. This ensures reproducibility and prevents user-entered errors.

## 2. Boundary retrieval via OSMnx
Using the municipality name and state, the script calls `osmnx.geocode_to_gdf()` to obtain the municipal boundary polygon. If no polygon is returned, the algorithm informs the user and halts.

## 3. Optional buffering
If a buffer distance is provided, the polygon is projected to a metric CRS, buffered by the specified number of meters, and reprojected to WGS84. This is useful for metropolitan-scale or peri-urban analyses.

## 4. Street-network extraction
Using the boundary polygon, the script calls `osmnx.graph_from_polygon()`, retrieving a filtered, topologically correct street network for the chosen network type.

## 5. Automatic UTM projection
The network is projected using `ox.project_graph()`, ensuring accurate geometric and topological computations.

## 6. Conversion to GeoDataFrames
Nodes and edges are converted to GeoPandas GeoDataFrames [@geopandas2020]. Only edges (street segments) are exported.

## 7. CRS handling and export
Due to known Windows QGIS issues involving PROJ and Fiona, the tool removes the CRS attribute before export, preventing errors such as *“Could not set CRS: EPSG:32722”*. Users may reassign the correct CRS in QGIS.

## 8. Automatic layer loading
The exported dataset is added directly to the QGIS project with a descriptive name encoding municipality, state, network type, and buffer information.

This workflow produces a clean, GIS-ready dataset and ensures consistency across analyses involving multiple municipalities.

# Software Design and Implementation

The software follows the QGIS Processing Framework architecture, which structures tasks into parameter definitions, algorithm logic, and output handling. The script extends the `QgsProcessingAlgorithm` class and uses QGIS Python API components like:

- `QgsProcessingParameterString`
- `QgsProcessingParameterEnum`
- `QgsProcessingParameterNumber`
- `QgsProcessingParameterFileDestination`
- `QgsVectorLayer` and `QgsProject`

## Dependencies

The tool relies on widely used open-source geospatial libraries:

- **OSMnx** for geocoding, network extraction, projection, and graph management [@osmnx_github].
- **GeoPandas** for vector data handling [@geopandas2020].
- **Shapely** for geometric operations [@shapely].
- **PyProj** for CRS and projection operations [@pyproj].
- **Requests** for IBGE API access.

## Internal structure

The architecture is divided into functional blocks:

- API queries  
- Boundary retrieval  
- Buffering and projection  
- Network extraction  
- Graph conversion  
- File output  
- QGIS layer integration  
- Error diagnostics  

Each block is isolated for clarity and maintainability.

## Error handling

The tool includes clear, user-friendly error messages for:

- Invalid IBGE codes  
- Connection failures  
- Missing Python dependencies  
- Empty or invalid boundaries  
- Projection inconsistencies  
- File export errors  

This improves usability for non-expert users.

## Performance considerations

- OSMnx caching greatly reduces repeated download time.
- CRS transformations are minimized.
- GeoDataFrame operations are restricted to essential steps.

# Research Applications

The tool is versatile across several research domains:

## Urban morphology
- Segment map generation  
- Centrality measures (betweenness, closeness, potential movement)  
- Morphological classification and typology studies  

## Transportation and mobility
- Routing analysis and multimodal assessment  
- Network resilience studies  
- Local and regional connectivity evaluation  

## Accessibility modeling
- Isochrone computation  
- Gravity-based accessibility  
- Integration with land-use layers  

## Environmental and climate-risk analysis
- Flood-exposure modeling  
- Evacuation route simulation  
- Infrastructure vulnerability assessment  

## Pedagogical applications
The tool is ideal for teaching GIS, planning, and spatial analysis, allowing students to retrieve real-world data with minimal setup.

# Acknowledgements

The author thanks the developers of OSMnx, GeoPandas, PyProj, QGIS, and the contributors to OpenStreetMap for maintaining essential open-source geospatial tools. The IBGE Localidades API provides the standardized municipal data infrastructure that makes this workflow possible.

# References
