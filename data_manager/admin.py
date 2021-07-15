from django.contrib import admin
from data_manager.models import Dataset, Project, Person, PersonTypeRole, Publisher, Keyword, BasisOfRecord, \
    DataType, GBIFVerbatimOccurrence, GBIFOccurrence, HexGrid, Download, HarvestedDataset


class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'project', 'get_keywords'
    )
    search_fields = ('title', 'project')
    empty_value_display = '-empty-'


class GBIFOccurrenceAdmin(admin.ModelAdmin):
    list_display = (
        'gbifID', 'dataset'
    )
    search_fields = ('row_json_text',)


class PersonTypeRoleAdmin(admin.ModelAdmin):
    list_display = (
        'person', 'person_type', 'role', 'dataset'
    )
    search_fields = ('person__full_name', 'dataset__title')


class HarvestedDatasetAdmin(admin.ModelAdmin):
    list_filter = ('include_in_antabif', 'import_full_dataset', 'type', 'deleted_from_gbif', 'harvested_on')
    list_display = ('title', 'type', 'include_in_antabif', 'import_full_dataset', 'dataset', 'harvested_on')
    search_fields = ('hostingOrganizationKey', 'key', 'title')


# Register your models here.
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(DataType)
admin.site.register(Project)
admin.site.register(Person)
admin.site.register(PersonTypeRole, PersonTypeRoleAdmin)
admin.site.register(Publisher)
admin.site.register(Keyword)
admin.site.register(BasisOfRecord)
admin.site.register(GBIFVerbatimOccurrence)
admin.site.register(GBIFOccurrence, GBIFOccurrenceAdmin)
admin.site.register(HexGrid)
admin.site.register(Download)
admin.site.register(HarvestedDataset, HarvestedDatasetAdmin)
