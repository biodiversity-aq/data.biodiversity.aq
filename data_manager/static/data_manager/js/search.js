/*
    JavaScript/jQuery for occurrence_list.html
    Use to render ui for facetted search filter
*/

/*
    Required jQueryUI library
    Function to create range slider for latitude and longitude
*/

function latLongRangeSlider( sliderId, rangeDict, minInputID, maxInputID, minCoord, maxCoord ){
        $( function() {
            $( sliderId ).slider({
                range: true,
                min: minCoord,
                max: maxCoord,
                values: [ rangeDict[0], rangeDict[1] ],
                slide: function( event, ui ) {
                    //$( textLabelID ).val( ui.values[ 0 ] + " to " + ui.values[ 1 ] );
                    /* input for decimal_latitude field of filter-form */
                    $( minInputID ).val( ui.values[ 0 ]);  // min
                    $( maxInputID ).val( ui.values[ 1 ]);  // max
                }
            });  // slider

            /* setter: set values for hidden input and text input which display the values of slider */
            //$( textLabelID ).val( $( sliderId ).slider( "values", 0 ) + " to " + $( sliderId ).slider( "values", 1 ) );
            $( minInputID ).val( $( sliderId ).slider( "values", 0 ) );
            $( maxInputID ).val( $( sliderId ).slider( "values", 1 ) );
        });  // function
    };  // latLongRangeSlider


/* Function to reset form
Happens when user click on reset button*/
function resetForm() {
    // clear search term
    $('#id_q').val('');
    // clear taxon hidden input
    $('#id_taxon').val('');
    // clear select input
    $('#id_dataset').prop('selectedIndex',0);
    // clear all checkboxes
    $('input:checkbox').prop('checked', false);
    // reset values for lat long slider
    var latitudeRange = [-90.0, 90.0];
    var longitudeRange = [-180.0, 180.0];

    latLongRangeSlider("#latitude-range", latitudeRange, "#id_decimal_latitude_0", "#id_decimal_latitude_1", -90.0, 90.0);
    latLongRangeSlider("#longitude-range", longitudeRange,"#id_decimal_longitude_0", "#id_decimal_longitude_1", -180.0, 180.0);
}

function getFilterValues(queryParams) {
    var div = document.getElementById('search-filters');
    // fire GET request of the page
    $.get(apiSearchFilter, function(data, status){
        // put the data obtained into #results-container
        div.innerHTML += `${data}`;
        // call function to create and populate latitude & longitude range slider widget
        latLongRangeSlider("#latitude-range", latitudeRange, "#id_decimal_latitude_0", "#id_decimal_latitude_1",
        -90.00, 90.00);
        latLongRangeSlider("#longitude-range", longitudeRange, "#id_decimal_longitude_0", "#id_decimal_longitude_1",
        -180.00, 180.00);
    })
}

/* To GET the number of records found from a search */
function getCount(queryParams) {
    // get the #results-count div
    var div = document.getElementById('results-count');
    // fire GET request of the page
    $.get(resultsCount, function(data, status){
        // put the data obtained into #results-container
        div.innerHTML += `${data.count} records found`;
    });
}

/* To GET the GBIFOccurrence records from a search results page (with limit/offset) */
function getPage(queryParams) {
    // get the #results-table div
    var div = document.getElementById('results-table');
    // fire GET request of the page
    $.get(apiSearch, function(data, status){
        // put the data obtained into #results-container
        div.innerHTML += `${data}`;
    });

}
