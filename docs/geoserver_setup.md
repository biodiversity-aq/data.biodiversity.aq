# Geoserver setup for data.biodiversity.aq

Once GeoServer is installed, run it (for local development) using its startup script:

```
./bin/startup.sh
```

Now you can access the GeoServer admin page at `localhost:8080/geoserver`. By default,
you can log in with user `admin` and password `geoserver`. If you change the password,
make sure you keep it in a safe place.

Our data portal uses several layers and groups. Follow the steps below to get everything set up.

## Workspaces

Add new workspace:

```
Name: antabif  
Namespace URI: http://data.biodiversity.aq/ (or http://localhost:8080/antabif for local dev)
```

## Styles
Styles for the layers. Remember to select styles under `Publishing` tab when publishing new layers.

4 styles need to be added:

1. antarctica\_basemap\_polygon
2. subantarctic\_basemap\_polygon
3. dataset\_heatmap
4. hexbin

### 1. antarctica\_basemap\_polygon
This style is for `cst10_polygon` layer. It colors the polygon with white outline so that it is apparent in the data portal which has black background for maps.

**Style Data**

```
Name: antarctica_basemap_polygon
Workspace: antabif
Format: SLD
```
**Style Editor**

```
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
 xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
 xmlns="http://www.opengis.net/sld" 
 xmlns:ogc="http://www.opengis.net/ogc" 
 xmlns:xlink="http://www.w3.org/1999/xlink" 
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <!-- a Named Layer is the basic building block of an SLD document -->
  <NamedLayer>
    <Name>basemap_polygon</Name>
    <UserStyle>
    <!-- Styles can have names, titles and abstracts -->
      <Title>Basemap Polygon</Title>
      <Abstract>Basemap polygon for Antarctica map in data.biodiversity.aq</Abstract>
      <!-- FeatureTypeStyles describe how to render different features -->
      <!-- A FeatureTypeStyle for rendering polygons -->
      <FeatureTypeStyle>
        <Rule>
         <Name>iceshelf</Name>
         <Title>iceshelf</Title>
         <ogc:Filter>
           <ogc:PropertyIsEqualTo >
             <ogc:PropertyName>cst10srf</ogc:PropertyName>
             <ogc:Literal>iceshelf</ogc:Literal>
           </ogc:PropertyIsEqualTo >
         </ogc:Filter>
         <PolygonSymbolizer>
           <Stroke>
           	<CssParameter name="stroke">#ffffff</CssParameter>
           	<CssParameter name="stroke-width">0.7</CssParameter>
           </Stroke>
         </PolygonSymbolizer>
     	</Rule>
        <Rule>
         <Name>land</Name>
         <Title>land</Title>
         <ogc:Filter>
           <ogc:PropertyIsEqualTo >
             <ogc:PropertyName>cst10srf</ogc:PropertyName>
             <ogc:Literal>land</ogc:Literal>
           </ogc:PropertyIsEqualTo >
         </ogc:Filter>
         <PolygonSymbolizer>
           <Stroke>
           	<CssParameter name="stroke">#ffffff</CssParameter>
           	<CssParameter name="stroke-width">0.7</CssParameter>
           </Stroke>
         </PolygonSymbolizer>
     	</Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
```
<span style="color:blue">**Submit**</span>

### 2. subantarctic\_basemap\_polygon

This style is for `coastline_sub` layer. It colors the polygon with white outline so that it is apparent in the data portal which has black background for maps. It cannot reuse the style above because the property name is different

**Style Data**

```
Name: subantarctic_basemap_polygon
Workspace: antabif
Format: SLD
```
**Style Editor**

```
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
 xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
 xmlns="http://www.opengis.net/sld" 
 xmlns:ogc="http://www.opengis.net/ogc" 
 xmlns:xlink="http://www.w3.org/1999/xlink" 
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <!-- a Named Layer is the basic building block of an SLD document -->
  <NamedLayer>
    <Name>subantarctic_polygon</Name>
    <UserStyle>
    <!-- Styles can have names, titles and abstracts -->
      <Title>subantarctic polygon</Title>
      <Abstract>style for subantarctic polygon in data.biodiversity.aq</Abstract>
      <!-- FeatureTypeStyles describe how to render different features -->
      <!-- A FeatureTypeStyle for rendering polygons -->
      <FeatureTypeStyle>
        <Rule>
          <Name>rule1</Name>
          <Title>Polygon with stroke and no fill</Title>
          <Abstract>A polygon with a white outline</Abstract>
          <PolygonSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#ffffff</CssParameter>
              <CssParameter name="stroke-width">0.7</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
```
<span style="color:blue">**Submit**</span>

### 3. hexbin

This style is for the `hexagon_grid_counts_all` layer

**Style Data**

```
Name: hexbin
Workspace: antabif
Format: SLD
```
**Style Editor**

```
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
 xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
 xmlns="http://www.opengis.net/sld"
 xmlns:ogc="http://www.opengis.net/ogc"
 xmlns:xlink="http://www.w3.org/1999/xlink"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <!-- a Named Layer is the basic building block of an SLD document -->
  <NamedLayer>
    <Name>hexbin</Name>
    <UserStyle>
    <!-- Styles can have names, titles and abstracts -->
      <Title>Hexagon heatmap</Title>
      <Abstract>Hexagon binning, colour based on count value generated by SQL view</Abstract>
      <!-- FeatureTypeStyles describe how to render different features -->
      <!-- A FeatureTypeStyle for rendering polygons -->
      <FeatureTypeStyle>
       <Rule>
       <Name>Level0</Name>
       <ogc:Filter>
         <ogc:PropertyIsEqualTo>
           <ogc:PropertyName>category</ogc:PropertyName>
           <ogc:Literal>0</ogc:Literal>
         </ogc:PropertyIsEqualTo>
       </ogc:Filter>
       <PolygonSymbolizer>
         <Fill>
           <CssParameter name="fill">#4575b4</CssParameter>
           <CssParameter name="fill-opacity">0</CssParameter>
         </Fill>
       </PolygonSymbolizer>
     </Rule>
     <Rule>
       <Name>Level1</Name>
       <ogc:Filter>
         <ogc:PropertyIsEqualTo>
           <ogc:PropertyName>category</ogc:PropertyName>
           <ogc:Literal>1</ogc:Literal>
         </ogc:PropertyIsEqualTo>
       </ogc:Filter>
       <PolygonSymbolizer>
         <Fill>
           <CssParameter name="fill">#4575b4</CssParameter>
           <CssParameter name="fill-opacity">0.8</CssParameter>
         </Fill>
       </PolygonSymbolizer>
     </Rule>
     <Rule>
       <Name>Level2</Name>
       <ogc:Filter>
         <ogc:PropertyIsEqualTo>
           <ogc:PropertyName>category</ogc:PropertyName>
           <ogc:Literal>2</ogc:Literal>
         </ogc:PropertyIsEqualTo>
       </ogc:Filter>
       <PolygonSymbolizer>
         <Fill>
           <CssParameter name="fill">#91bfdb</CssParameter>
           <CssParameter name="fill-opacity">0.8</CssParameter>
         </Fill>
       </PolygonSymbolizer>
     </Rule>
     <Rule>
       <Name>Level3</Name>
       <ogc:Filter>
         <ogc:PropertyIsEqualTo>
           <ogc:PropertyName>category</ogc:PropertyName>
           <ogc:Literal>3</ogc:Literal>
         </ogc:PropertyIsEqualTo>
       </ogc:Filter>
       <PolygonSymbolizer>
         <Fill>
           <CssParameter name="fill">#e0f3f8</CssParameter>
           <CssParameter name="fill-opacity">0.8</CssParameter>
         </Fill>
       </PolygonSymbolizer>
     </Rule>
     <Rule>
       <Name>Level4</Name>
       <ogc:Filter>
         <ogc:PropertyIsEqualTo>
           <ogc:PropertyName>category</ogc:PropertyName>
           <ogc:Literal>4</ogc:Literal>
         </ogc:PropertyIsEqualTo>
       </ogc:Filter>
       <PolygonSymbolizer>
         <Fill>
           <CssParameter name="fill">#fee090</CssParameter>
           <CssParameter name="fill-opacity">0.8</CssParameter>
         </Fill>
       </PolygonSymbolizer>
     </Rule>
     <Rule>
       <Name>Level5</Name>
       <ogc:Filter>
         <ogc:PropertyIsEqualTo>
           <ogc:PropertyName>category</ogc:PropertyName>
           <ogc:Literal>5</ogc:Literal>
         </ogc:PropertyIsEqualTo>
       </ogc:Filter>
       <PolygonSymbolizer>
         <Fill>
           <CssParameter name="fill">#fc8d59</CssParameter>
           <CssParameter name="fill-opacity">0.8</CssParameter>
         </Fill>
       </PolygonSymbolizer>
     </Rule>
     <Rule>
       <Name>Level6</Name>
       <ogc:Filter>
         <ogc:PropertyIsEqualTo>
           <ogc:PropertyName>category</ogc:PropertyName>
           <ogc:Literal>6</ogc:Literal>
         </ogc:PropertyIsEqualTo>
       </ogc:Filter>
       <PolygonSymbolizer>
         <Fill>
           <CssParameter name="fill">#d73027</CssParameter>
           <CssParameter name="fill-opacity">0.8</CssParameter>
         </Fill>
       </PolygonSymbolizer>
     </Rule>
   </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
```
<span style="color:blue">**Submit**</span>

## Stores
Layers will be created together with stores. 2 Stores will be created:

1. Shapefiles
2. PostGIS

### Add custom CRS

First add a custom CRS (Otherwise the `coastline_sub` layer cannot be published).
To do so, open the `epsg.properties` file in the GeoServer data directory (in my case
that was in `data_dir/user_projections`.) At the last line, add:

```
102020=PROJCS["South_Pole_Lambert_Azimuthal_Equal_Area", GEOGCS["WGS 84", DATUM["WGS_1984", SPHEROID["WGS 84", 6378137.0, 298.257223563]], PRIMEM["Greenwich", 0.0], UNIT["degree", 0.017453292519943295], AXIS["Longitude", EAST], AXIS["Latitude", NORTH]], PROJECTION["Lambert_Azimuthal_Equal_Area"], PARAMETER["latitude_of_center", -90.0], PARAMETER["longitude_of_center", 0.0], PARAMETER["false_easting", 0.0], PARAMETER["false_northing", 0.0], UNIT["m", 1.0], AXIS["x", EAST], AXIS["y", NORTH], AUTHORITY["EPSG","102020"]]
```

That should be on one line.

### A. Shapefiles store

Add new Store > Vector Data Sources

#### Basic Store Info

```
Workspace: antabif
Data Source Name *: shps
Description:  
[x] Enabled
```

#### Connection Parameters

Directory of shapefiles is the directory that contains:

* coastline_sub
* cst10_polygon

with these file types: .cst, .dbf, .prj, .qix, .shp, .shx

```
Directory of shapefiles *:
file:///Users/biodiversityaq/Desktop/data.biodiversity.aq.geoserver.rest/

DBF files charset: ISO-8859-1

[x] Create spatial index if missing/outdated
[ ] Use memory mapped buffers (Disable on Windows)
[x] Cache and reuse memory maps (Requires 'Use Memory mapped buffers' to be enabled)
```
<span style="color:blue">**Save**</span>

### Shapefiles Layers

```
Layer name				Action
coastline_sub			Publish
cst10_polygon			Publish
```

#### 1. Publish `coastline_sub`	

antabif:coastline_sub
Configure the resource and publishing information for the current layer

##### Data 

```
Name: coastline_sub
[x] Enabled
[x] Advertised

Title: coastline_sub

Coordinate Reference Systems
Native SRS: EPSG:102020	  EPSG:South_Pole_Lambert_Azimuthal_Equal_Area...
Declared SRS: EPSG:3031   EPSG:WGS 84 / Antarctic Polar Stereographic...
SRS handling: Reproject native to declared

Bounding Boxes
Native Bounding Box
[x] Compute from data
[ ] Compute from SRS bounds

Lat/Lon Bounding Box
[x] Compute from native bounds
```

##### Publishing

```
WMS Settings
Layer Settings

[x] Queryable
[ ] Opaque
Default Style: antabif:subantarctic_basemap_polygon
```

<span style="color:blue">**Save**</span>

#### 2. Publish `cst10_polygon`	

antabif:cst10_polygon
Configure the resource and publishing information for the current layer

##### Data 

```
Name: cst10_polygon
[x] Enabled
[x] Advertised

Title: cst10_polygon

Coordinate Reference Systems
Native SRS: UNKNOWN	  WGS_1984_Antarctic_Polar_Stereographic...
Declared SRS: EPSG:3031   EPSG:WGS 84 / Antarctic Polar Stereographic...
SRS handling: Force declared

Bounding Boxes
Native Bounding Box
[x] Compute from data
[ ] Compute from SRS bounds

Lat/Lon Bounding Box
[x] Compute from native bounds
```

##### Publishing

```
WMS Settings
Layer Settings

[x] Queryable
[ ] Opaque
Default Style: antabif:antarctica_basemap_polygon
```

<span style="color:blue">**Save**</span>

---

### B. data\_biodiversity\_aq store

Add new Store > Vector Data Sources > PostGIS

#### Basic Store Info

```
Workspace: antabif
Data Source Name *: data_biodiversity_aq
Description: 
[x] Enabled
```

#### Connection Parameters

```
dbtype *: postgis
host *: localhost
port *: 5432
database: data_biodiversity_aq
schema: public
user *: dev_rw
passwd *: *****
Namespace * data.biodiversity.aq

# Following are default values
max connections: 10
min connections: 1
fetch size: 1000
Batch insert size: 1
Connection timeout: 20
[x] validate connections
[x] Test while idle
Evictor run periodicity: 300
Max connection idle time: 300
Evictor tests per run: 3

[x] Loose bbox
[x] Estimated extends
Max open prepared statements: 50
[x] Support on the fly geometry simplification
```
<span style="color:blue">**Save**</span>

### data\_biodiversity\_aq Layers

2 layers and 1 layer group will be created for this store:

Layers:

1. hexagon\_grid\_counts_all
2. data\_manager\_gbifoccurrence

Layer group:

3. antarctica\_basemap
Layers > Add a new layer

---

#### 1. hexagon\_grid\_counts_all layer
Add layer from: antabif:data\_biodiversity\_aq

##### Data 

```
Name: hexagon_grid_counts_all
[x] Enabled
[x] Advertised

Title: hexagon_grid_counts_all

Coordinate Reference Systems
Native SRS: EPSG:3031   EPSG:WGS 84 / Antarctic Polar Stereographic...
Declared SRS: EPSG:3031   EPSG:WGS 84 / Antarctic Polar Stereographic...
SRS handling: Keep native

Bounding Boxes
Native Bounding Box
[x] Compute from data
[ ] Compute from SRS bounds

Lat/Lon Bounding Box
[x] Compute from native bounds
```

##### Publishing

```
WMS Settings
Layer Settings

[x] Queryable
[ ] Opaque
Default Style: antabif:hexbin
```
<span style="color:blue">**Save**</span>

#### 2. data\_manager\_gbifoccurrence layer
Add layer from: antabif:data\_biodiversity\_aq

##### Data 

```
Name: data_manager_gbifoccurrence
[x] Enabled
[x] Advertised

Title: data_manager_gbifoccurrence

Coordinate Reference Systems
Native SRS: EPSG:4326   EPSG:WGS 84...
Declared SRS: EPSG:3031   EPSG:WGS 84 / Antarctic Polar Stereographic...
SRS handling: Reproject native to declared

Bounding Boxes
Native Bounding Box
[x] Compute from data
[ ] Compute from SRS bounds

Lat/Lon Bounding Box
[x] Compute from native bounds
```

##### Publishing

```
WMS Settings
Layer Settings

[x] Queryable
[ ] Opaque
Default Style: antabif:dataset_heatmap
```
<span style="color:blue">**Save**</span>

#### 3. antarctica\_basemap layer group

##### Data 

```
Name: antarctica_basemap
[x] Enabled
[x] Advertised

Title: antarctica_basemap
Abstract: Antarctica basemap combining Quantarctica antarctic basemap and subantarctic map downloaded from gis.ccamlr.org

Workspace: antabif
Coordinate Reference Systems
EPSG:3031   EPSG:WGS 84 / Antarctic Polar Stereographic...
[ ] Generate Bounds
[x] Generate Bounds from CRS

Mode: Single
[x] Queryable

Add layer
Layer								Style
[x] antabif:cst10_polygon			antarctica_basemap_polygon
[x] antabif:coastline_sub			subantarctic_basemap_polygon
```

<span style="color:blue">**Save**</span>

---

### Run GeoServer locally
Go to the directory of geoserver/bin, e.g.: `/usr/local/geoserver/bin` on terminal. Run

```
sh startup.sh
```
Open your browser, go to [localhost:8080/geoserver](localhost:8080/geoserver). 
