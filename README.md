# São Paulo Violence Heatmap

An interactive geospatial analysis project that visualizes patterns of urban violence in São Paulo using heatmaps based on publicly available data.

This project aims to support data-driven discussions about public safety, urban planning, and social awareness by transforming raw crime statistics into intuitive geographic visualizations.

---

## Project Overview

The project processes public security data from São Paulo and generates an interactive **heatmap** that highlights areas with higher concentrations of violent incidents over a given period.

Key goals:
- Transform raw crime data into geospatial insights
- Aggregate incidents by administrative regions (districts or neighborhoods)
- Provide a clear and ethical visualization (no exact addresses)
- Enable easy exploration via a web-based map

---

## Data Sources

- **São Paulo State Public Security Secretariat (SSP-SP)**
- **São Paulo Open Data Portal**
- **GeoSampa** (official geospatial data from São Paulo City Hall)
- **IBGE** (administrative boundaries)

> All data used in this project is publicly available.

---

## Tech Stack

### Core
- **Python 3.10+**
- **pandas** – data cleaning and transformation
- **GeoPandas** – geospatial processing
- **Shapely / PyProj** – geometry and projections

### Geocoding & Maps
- **OpenStreetMap / Nominatim** – geocoding
- **Folium (Leaflet.js)** – interactive maps
- **Folium HeatMap plugin**

### Storage & Formats
- CSV / Parquet
- GeoJSON / Shapefiles

---

## Project Structure

```text
sp-violence-heatmap/
├── data/
│   ├── raw/            # Original datasets
│   ├── processed/      # Cleaned and aggregated data
│   └── geo/            # Shapefiles / GeoJSON
├── notebooks/          # Exploratory analysis
├── src/
│   ├── ingest.py       # Data ingestion
│   ├── clean.py        # Data cleaning
│   ├── geocode.py      # Geocoding logic
│   └── map.py          # Heatmap generation
├── output/
│   └── heatmap.html    # Final interactive map
└── README.md

