# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

  
## [1.3.2](https://git.bebif.be/antabif/data.biodiversity.aq/-/tags/v1.3.2) - 2021-05-03

### Changed

- Increase download size. (@[ymgan](https://git.bebif.be/ymgan))
- Upgrade dependencies. (@[ymgan](https://git.bebif.be/ymgan))
- Convert HarvestedDatasetViewSet to ReadOnlyModelViewSet and set permission to anon. (@[ymgan](https://git.bebif.be/ymgan))
- Show HarvestedDatasetViewSet in swagger. (@[ymgan](https://git.bebif.be/ymgan))


## [1.3.1](https://git.bebif.be/antabif/data.biodiversity.aq/-/tags/v1.3.1) - 2020-09-04

### Added

- A migration to remove orphaned `Project` instance.
[#77](https://git.bebif.be/antabif/data.biodiversity.aq/issues/77) (@[ymgan](https://git.bebif.be/ymgan))


- Temporarily disable verbatim import.
[#91](https://git.bebif.be/antabif/data.biodiversity.aq/issues/91) (@[ymgan](https://git.bebif.be/ymgan))

## [1.3.0](https://git.bebif.be/antabif/data.biodiversity.aq/-/tags/v1.3.0) - 2020-08-12

### Changed

- Additional internal filter to remove irrelevant dataset harvested. 
[#90](https://git.bebif.be/antabif/data.biodiversity.aq/-/issues/90) (@[ymgan](https://git.bebif.be/ymgan))

## [1.2.1](https://git.bebif.be/antabif/data.biodiversity.aq/-/tags/v1.2.1) - 2020-07-10

### Added

- A migration to remove unwanted `HarvestedDataset` instance returned from GBIF dataset search.
[#89](https://git.bebif.be/antabif/data.biodiversity.aq/issues/89) (@[ymgan](https://git.bebif.be/ymgan))

### Changed

- Change harvest query to remove unspecific search terms
[#89](https://git.bebif.be/antabif/data.biodiversity.aq/issues/89) (@[ymgan](https://git.bebif.be/ymgan))
- Create download directory if it does not exists.

## [1.2.0] (https://git.bebif.be/antabif/data.biodiversity.aq/-/tags/v1.2.0) - 2020-06-16

### Added
- Timestamp for first created and last modified for `Dataset`. 
[#81](https://git.bebif.be/antabif/data.biodiversity.aq/issues/87) (@[ymgan](https://git.bebif.be/ymgan))


### Changed

- Update import script to only import fields specified in `GBIFOccurrence` and `GBIFVerbatimOccurrence`. 
[#81](https://git.bebif.be/antabif/data.biodiversity.aq/issues/81) (@[ymgan](https://git.bebif.be/ymgan))
- Perform binning after the whole import is completed instead of per dataset. 
[#81](https://git.bebif.be/antabif/data.biodiversity.aq/issues/81) (@[ymgan](https://git.bebif.be/ymgan))
- Update tests for import script and managers. 
[#81](https://git.bebif.be/antabif/data.biodiversity.aq/issues/81) (@[ymgan](https://git.bebif.be/ymgan))

### Removed

- Remove fields from `GBIFOccurrence` and `GBIFVerbatimOccurrence` that are not used in app. 
[#81](https://git.bebif.be/antabif/data.biodiversity.aq/issues/81) (@[ymgan](https://git.bebif.be/ymgan))
- Remove dependency `Pympler`, no longer used. (@[ymgan](https://git.bebif.be/ymgan))
- Remove google form on help page. (@[ymgan](https://git.bebif.be/ymgan))

## [1.1](https://git.bebif.be/antabif/data.biodiversity.aq/-/tags/v1.1) - 2020-04-01

### Added

- `DEFAULT_API_URL` setting. [#82](https://git.bebif.be/antabif/data.biodiversity.aq/issues/82) 
(@[ymgan](https://git.bebif.be/ymgan))
- `BasisOfRecordManager` to manage `BasisOfRecord` instances from dwca.rows.Row object.

### Changed

- Cancel download request to GBIF if it takes more than 3 hours to generate a download. 
[#78](https://git.bebif.be/antabif/data.biodiversity.aq/issues/78) (@[ymgan](https://git.bebif.be/ymgan))

### Fixed

- Fix scheme (`https` for production site) used in Swagger UI by adding`DEFAULT_API_URL` setting. 
[#82](https://git.bebif.be/antabif/data.biodiversity.aq/issues/82) (@[ymgan](https://git.bebif.be/ymgan))
- Fix inconsistent GBIFOccurrence QuerySet in download generation when GET request is passed to Celery as QueryDict. 
(@[ymgan](https://git.bebif.be/ymgan))

### Removed

- Synchronous `Dataset` and `GBIFOccurrence` download and their tests. They are no longer used. 
(@[ymgan](https://git.bebif.be/ymgan))
- Remove `USE_BACKGROUND_DOWNLOADS` settings. (@[ymgan](https://git.bebif.be/ymgan))

