# API documentation

Base url: https://data.biodiversity.aq/api/v1.0/ <br/>
Swagger: https://data.biodiversity.aq/api/v1.0/swagger

---

## Paging

The following parameters are used for requests that support paging:

Parameter | Explanation
--- | --- 
limit | The number of results in a page. Default to 20 results per page.
offset | Determines the offset for the search results.  

## Authentication

Some requests require authentication. This API uses HTTP basic access authentication with any 
[biodiversity.aq](https://data.biodiversity.aq/login/) that you have created before. 
Your username is the email registered for your account. 

## API

Class | Resource url | Method | Response | Description | Auth | Paging | Parameter | Lookup type
--- | --- | --- | --- | --- | --- | --- | --- | ---
Dataset | /dataset/ | GET | [Dataset List](http://data.biodiversity.aq/api/v1.0/dataset/) | Lists all datasets sorted by descending record count | False | True | q | case-insensitive full text search
| | | | | | | | dataType | associated DataType ID(s) in the iterables provided
| | | | | | | | keyword | associated Keyword ID(s) in the iterables provided
| | | | | | | | publisher | associated Publisher ID(s) in the iterables provided
| | | | | | | | projectPersonnel | associated ProjectPersonnel ID(s) in the iterables provided
| | | | | | | | project | associated Project ID(s) in the iterables provided
| | /dataset/{id}/ | GET | [Dataset](http://data.biodiversity.aq/api/v1.0/dataset/1/) | Retrieve the details of a single dataset | False | False | |
Basis of record | /basis-of-record/ | GET | [BasisOfRecord List](http://data.biodiversity.aq/api/v1.0/basis-of-record/) | Lists all basis of record ordered alphabetically | False | True |  | 
| | /basis-of-record/{id}/ | GET | [BasisOfRecord](http://data.biodiversity.aq/api/v1.0/basis-of-record/1/) | Retrieve the details of a single basis of record | False | False | | |
Data type | /data-type/ | GET | [DataType List](http://data.biodiversity.aq/api/v1.0/data-type/) | Lists all data type ordered alphabetically | False | True |  | 
| | /data-type/{id}/ | GET | [DataType](http://data.biodiversity.aq/api/v1.0/data-type/1/) | Retrieve the details of a single data type | False | False | | |
Keyword | /keyword/ | GET | [Keyword List](http://data.biodiversity.aq/api/v1.0/keyword/) | Lists all keywords ordered alphabetically | False | True | search | case-insensitive containment test on `keyword` field
| | /keyword/{id}/ | GET | [Keyword](http://data.biodiversity.aq/api/v1.0/keyword/1/) | Retrieve the details of a single keyword | False | False | | |
Project | /project/ | GET | [Project List](http://data.biodiversity.aq/api/v1.0/project/) | Lists all projects ordered alphabetically | False | True | search | case-insensitive containment test on `title` field
| | /project/{id}/ | GET | [Project](http://data.biodiversity.aq/api/v1.0/project/1/) | Retrieve the details of a single project | False | False | | |
ProjectPersonnel | /project-personnel/ | GET | [ProjectPersonnel List](http://data.biodiversity.aq/api/v1.0/project-personnel/) | Lists all project personnel | False | True | search | case-insensitive containment test on `fullName` field
| | /project/{id}/ | GET | [ProjectPersonnel](http://data.biodiversity.aq/api/v1.0/project-personnel/1/) | Retrieve the details of a single project personnel | False | False | |
Publisher | /publisher/ | GET | [Publisher List](http://data.biodiversity.aq/api/v1.0/publisher/) | Lists all publisher ordered by publisher name alphabetically | False | True | search | case-insensitive containment test on `publisherName` field
| | /publisher/{id}/ | GET | [Publisher](http://data.biodiversity.aq/api/v1.0/publisher/1/) | Retrieve the details of a single publisher | False | False | |
Occurrence | /occurrence/ | GET | [Occurrence List](http://data.biodiversity.aq/api/v1.0/occurrence/) | Lists all occurrences | False | True | q | case-insensitive full text search
| | | | | | | | scientific_name | case-insensitive containment test
| | | | | | | | taxon_key | exact 
| | | | | | | | decimal_latitude_min | greater than or equal to the value provided
| | | | | | | | decimal_latitude_max | less than or equal to the value provided
| | | | | | | | decimal_longitude_min | greater than or equal to the value provided
| | | | | | | | decimal_longitude_max | less than or equal to the value provided
| | | | | | | | depth_min | greater than or equal to the value provided
| | | | | | | | depth_max | less than or equal to the value provided
| | | | | | | | year_min | greater than or equal to the value provided
| | | | | | | | year_max | less than or equal to the value provided
| | | | | | | | month_min | greater than or equal to the value provided
| | | | | | | | month_max | less than or equal to the value provided
| | | | | | | | day_min | greater than or equal to the value provided
| | | | | | | | day_max | less than or equal to the value provided
| | | | | | | | locality | case-insensitive containment test 
| | | | | | | | samplingProtocol | case-insensitive containment test
| | | | | | | | occurrenceStatus | case-insensitive exact match
| | | | | | | | dataset | associated Dataset ID(s) in the iterables provided
| | | | | | | | basisOfRecord | associated BasisOfRecord ID(s) in the iterables provided
| | /occurrence/{id}/ | GET | [Occurrence](http://data.biodiversity.aq/api/v1.0/occurrence/1/) | Retrieve the details of a single occurrence | False | False | |
Download | /download/ | GET | [Download List](http://data.biodiversity.aq/api/v1.0/download/) | Lists all downloads created by the user authenticated within 7 days ordered by creation timestamp | True | True | |
| | /download/ | POST | ID, status, query | Create a download instance | True | False | query |
| | /download/{id}/ | GET |  | Retrieve the details of a single download | True | False | |
| | /download/{id}/ | DELETE | HTTP 204 No Content | Delete a single download | True | False | |

## Lookup types explained

Lookup type | Definition | Example
--- | --- | ---
case-sensitive | Uppercase and lowercase letters are treated as distinct | "Occurrence" is not equivalent to "occurrence"
case-insensitive | Uppercase and lowercase letters are treated as equivalent | "Occurrence" is equivalent to "occurrence" 
containment test | Value provided is a substring. Can be case-sensitive or case-insensitive. | "occur" is a substring of "Occurrence" (case-insensitive)


## Query parameters explained

Class | Parameter | Identifier | Description | Examples
--- | --- | --- | --- | ---
Dataset | q | | A search term | "Antarctic"
| | | | | "Antarctic jellyfish"
| | data_type | | DataType ID(s) | 1
| | | | | [1, 2]
| | keyword | | Keyword ID(s) | 1
| | | | | [1, 2]
| | publisher | | Publisher ID(s) | 1
| | | | | | [1, 2]
| | projectPersonnel | | ProjectPersonnel ID(s) | 1
| | | | | | [1, 2]
| | project | | Project ID(s) | 1
| | | | | [1, 2]
Occurrence | q | | A search term 
| | scientific_name | http://rs.tdwg.org/dwc/terms/scientificName | The full scientific name, with authorship and date information if known. When forming part of an Identification, this should be the name in lowest level taxonomic rank that can be determined. This term should not contain identification qualifications, which should instead be supplied in the IdentificationQualifier term.
| | taxon_key | http://rs.gbif.org/terms/1.0/taxonKey | The GBIF backbone key. 
| | decimal_latitude | http://rs.tdwg.org/dwc/terms/decimalLatitude | The geographic latitude (in decimal degrees, using the spatial reference system given in geodeticDatum) of the geographic center of a Location. Positive values are north of the Equator, negative values are south of it. Legal values lie between -90 and 90, inclusive. 
| | decimal_longitude | http://rs.tdwg.org/dwc/terms/decimalLongitude | The geographic longitude (in decimal degrees, using the spatial reference system given in geodeticDatum) of the geographic center of a Location. Positive values are east of the Greenwich Meridian, negative values are west of it. Legal values lie between -180 and 180, inclusive. 
| | depth | http://rs.gbif.org/terms/1.0/depth | Depth below the local surface, in meters. The depth is calculated using the equation: (minimumDepthInMeters + maximumDepthInMeters) / 2.
| | year | http://rs.tdwg.org/dwc/terms/year | The four-digit year in which the Event occurred, according to the Common Era Calendar.
| | month | http://rs.tdwg.org/dwc/terms/month | The ordinal month in which the Event occurred.
| | day | http://rs.tdwg.org/dwc/terms/day | The integer day of the month on which the Event occurred.
| | locality | http://rs.tdwg.org/dwc/terms/locality | The specific description of the place. Less specific geographic information can be provided in other geographic terms (higherGeography, continent, country, stateProvince, county, municipality, waterBody, island, islandGroup). This term may contain information modified from the original to correct perceived errors or standardize the description.
| | sampling_protocol | http://rs.tdwg.org/dwc/terms/samplingProtocol | The method or protocol used during an Event.
| | occurrence_status | http://rs.tdwg.org/dwc/terms/occurrenceStatus | A statement about the presence or absence of a Taxon at a Location.
| | dataset |  | A list of integer values identifying the Dataset
| | basis_of_record |  | A list of integer values identifying the BasisOfRecord


### Download query parameters

Parameter | Description | Example | Query explanation
--- | --- | --- | ---
query | JSON format of occurrence query parameters and its values | {"q" : "Antarctic jellyfish"} | Search for occurrences which contain the terms "Antarctic jellyfish"
| | |{"dataType": [1, 2], "keyword": [4], "phylum": "Echinodermata"} | Search for occurrences where: <br/>phylum == "Echinodermata" AND has keyword ID = 4 AND has `dataType` ID = 1 OR <br/>phylum = Echinodermata AND has keyword ID = 4 AND has `dataType` ID = 2 

### Example Occurrence Download

A query expression to retrieve occurrence record downloads with an example using `curl`. 
Save the following to a file named `query.json`.

```json
{
  "query": {
    "scientific_name": "Belgica antarctica Jacobs, 1900",
    "month_min": 1,
    "month_max": 3
  }
}
```

Run the following command in terminal to create a `POST` request to `CREATE` a Download instance.

```shell script
curl -i --user userName:password -H "Content-Type: application/json" -H "Accept: application/json" -X POST -d  @query.json https://data.biodiversity.aq/api/v1.0/download/                      
```

If successful, this will return a `HTTP 201 Created` response with the following information. An email will be sent to you once the download file is ready.

```json
{
    "id": 80,
    "status": "PREPARING",
    "downloadLink": "",
    "created": "2020-01-23T13:11:59.029755",
    "recordCount": null,
    "query": {
        "scientific_name": "Belgica antarctica Jacobs, 1900",
        "month_min": 1,
        "month_max": 3
    }
}
```
Once the status is `"SUCCESS"`, the `downloadLink` field will be populated.

Field | Example value | Description
--- | --- | ---
`id` | 80 | The ID of the download. Can be used to retrieve the detail of Download instance.
`status` | One of the values below | The process to generate the download file is asynchronous. There are a number of status. 
| | `PENDING` | Waiting for execution
| | `STARTED` | Task has been started
| | `SUCCESS` | Task executed successfully
| | `FAILURE` | Task execution failed
| | `RETRY` | Task is being retried
| | `REVOKED` | Task has been revoked
`downloadLink` | A url | The link to the download file generated
`created` | "2020-01-23T13:11:59.029755" | Timestamp when the Download request is received
`recordCount` | 10 | The number of records that matches the query
`query` | {"scientific_name": "Belgica antarctica Jacobs, 1900", "month_min": 1, "month_max": 3} | The query for the Download request in json format.



