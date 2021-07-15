/**
* @file Plot map dynamically
*
*/
var baseUrl;
var zoom;
var extent;
var occCount;


function plotMap (vectorUrl, target, baseLayerUrl) {
/**
* Plot map
*
* @param {String} vectorUrl - The url of serialised GIS features in GeoJson format
* @param {String} target - The id of target div in html
* @param {String} baseLayerUrl - The url where base layer is hosted (GeoServer in this case)
*
*/

    baseUrl = vectorUrl;

    // projection definition
    var projection = new ol.proj.Projection({
        code: 'EPSG:3031',
        units: 'm'
    });


    // map level to style (colour)
    var styles = {
            0: new ol.style.Style({
                fill: new ol.style.Fill({color: 'rgba(255,255,255,0)'}),
            }),
            1: new ol.style.Style({
                fill: new ol.style.Fill({color: 'rgba(44,123,182,0.7)'}),
            }),
            2: new ol.style.Style({
                fill: new ol.style.Fill({color: 'rgba(171,217,233,0.7)'}),
            }),
            3: new ol.style.Style({
                fill: new ol.style.Fill({color: 'rgba(255,255,191,0.7)'}),
            }),
            4: new ol.style.Style({
                fill: new ol.style.Fill({color: 'rgba(253,174,97,0.7)'}),
            }),
            5: new ol.style.Style({
                fill: new ol.style.Fill({color: 'rgba(215,25,28,0.7)'}),
            }),
        };

    // base layer
    var baseLayer = new ol.layer.Image({
        source: new ol.source.ImageWMS({
            attributions:'Base layer <a href="https://www.add.scar.org/">SCAR Antarctic Digital Database</a>',
            params: {
                'SERVICE': 'WMS',
                'VERSION': '1.1.1',
                'SRS': 'EPSG:3031',
                'LAYERS': 'antabif:antarctica_basemap',
                'FORMAT':'image/png',
                'TILED': true,
                'BUFFER': 0,
                'TRANSPARENT': true,
            },
            url: baseLayerUrl
        })
    });


    // occurrence map
    var occurrenceMap = new ol.Map({
        layers: [baseLayer],  // add vectorLayer later
        target: target,
        view: new ol.View({
            center: [0, 0],
            projection: projection,
            zoom: 3,
            minZoom: 3,
            maxZoom: 6,
        })
    });

    zoom = occurrenceMap.getView().getZoom();
    extent = occurrenceMap.getView().calculateExtent(occurrenceMap.getSize());
    var getOccurrenceCount = function(zoom, extent){
        let occCount = $.get(baseUrl, { count: true, zoom: zoom, extent: extent },
            function(data, status) {
            return data.results
        });
        return occCount };

    occCount = getOccurrenceCount(zoom, extent);

    // return a style for each feature based on the count.
    var styleFunction = function(feature){
        occCount.responseJSON.results.forEach(function(item){
            if (feature.get('pk') == item.pk) {
                var count = item.count;
                switch (true) {
                    case count == 0:
                        feature.set('count', count)  // set properties 'count' and 'level' to feature
                        feature.set('level', 0)
                        break;
                    case (count <= 10):
                        feature.set('count', count)
                        feature.set('level', 1)
                        break;
                    case (count <= 100):
                        feature.set('count', count)
                        feature.set('level', 2)
                        break;
                    case (count <= 1000):
                        feature.set('count', count)
                        feature.set('level', 3)
                        break;
                    case (count <= 10000):
                        feature.set('count', count)
                        feature.set('level', 4)
                        break;
                    case (count <= 100000):
                        feature.set('count', count)
                        feature.set('level', 5)
                        break;
                }
            }
        });
        return styles[feature.get('level')];
    };


    // vector source
    // Get features using GET request which contains the zoom level and extent of map to limit the
    // number of features returned.
    var vectorSource = new ol.source.Vector({
        format: new ol.format.GeoJSON(),
        url: function(extent, resolution, projection) {
            zoom = occurrenceMap.getView().getZoom();
            extent = occurrenceMap.getView().calculateExtent(occurrenceMap.getSize());
            // also need to reset count and level to new features obtained from new zoom and extent, hence
            // calling getOccurrenceCount() here
            occCount = getOccurrenceCount(zoom, extent);
        return baseUrl + '&zoom=' + zoom + '&extent=' + extent
        }
    });


    // vector layer: style and source
    var vectorLayer = new ol.layer.Vector({
        style: styleFunction,
        source: vectorSource
    });


    occurrenceMap.addLayer(vectorLayer);
    occurrenceMap.on('moveend', (function(){
        vectorSource.clear(); // reload the data
    }));

    // disable the scroll zoom
    occurrenceMap.getInteractions().forEach(function(interaction) {
        if (interaction instanceof ol.interaction.MouseWheelZoom) {
            interaction.setActive(false);
        }
    }, this);

    // tooltip
    var info = $('#info');
        info.tooltip({
            animation: false,
            trigger: 'manual'
        });

    var displayFeatureInfo = function(pixel) {
        info.css({
            left: pixel[0] + 'px',
            top: (pixel[1] - 10) + 'px'
        });
        var feature = occurrenceMap.forEachFeatureAtPixel(pixel, function(feature) {
            return feature;
        });
        if (feature) {
            info.tooltip('hide')
                .attr('data-original-title', 'occurrence count: ' + feature.get('count'))
                .tooltip('fixTitle')
                .tooltip('show');
        } else {
            info.tooltip('hide');
        }
    };

    occurrenceMap.on('pointermove', function(evt) {
        if (evt.dragging) {
            info.tooltip('hide');
            return;
        }
        displayFeatureInfo(occurrenceMap.getEventPixel(evt.originalEvent));
    });

};

