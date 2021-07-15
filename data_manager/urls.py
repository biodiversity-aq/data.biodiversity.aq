"""data_biodiversity_aq URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from data_manager.views import DatasetDownloadView, OccurrenceDownloadView, DatasetListView, DatasetDetailView, \
    occurrence_list_view_async, HomePageView, taxonListView, taxonDetailView, ContactView, PolicyView, HelpView, \
    DataSourceView, register, activate, DownloadsListView, get_download, dataset_activity, haproxy_view
from data_manager.rest_api_views import *
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, re_path, path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import routers, permissions
from rest_framework.urlpatterns import format_suffix_patterns


api_version = settings.REST_FRAMEWORK.get('DEFAULT_VERSION')

schema_view = get_schema_view(
    openapi.Info(
        title='Antarctic Biodiversity Data Portal API',
        default_version=api_version,
        description='',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url=settings.SWAGGER_SETTINGS.get('DEFAULT_API_URL')
)

# router
router = routers.DefaultRouter()
# viewset generates url patterns %(model_name)-detail & %(model_name)-list
router.register(r'harvested-dataset', HarvestedDatasetViewSet)
router.register(r'data-type', DataTypeViewSet, basename='datatype')
router.register(r'dataset', DatasetViewSet, basename='dataset')
router.register(r'keyword', KeywordViewSet, basename='keyword')
router.register(r'project', ProjectViewSet, basename='project')
router.register(r'basis-of-record', BasisOfRecordViewSet, basename='basisofrecord')
router.register(r'publisher', PublisherViewSet, basename='publisher')
router.register(r'occurrence', OccurrenceViewSet, basename='gbifoccurrence')
router.register(r'project-personnel', ProjectPersonnelViewSet, basename='projectpersonnel')

# urls for dataset
dataset_url_patterns = [
    re_path(r'^search/', DatasetListView.as_view(), name='dataset-search'),
    re_path(r'^download/$', DatasetDownloadView.as_view(), name='dataset-download'),
    re_path(r'^(?P<pk>[0-9]+)/$', DatasetDetailView.as_view(), name='dataset-detail-view'),
    re_path(r'^(?P<pk>[0-9]+)/activity/$', dataset_activity, name='dataset-activity')
]

# urls for taxon
taxon_url_patterns = [
    re_path(r'^search/', taxonListView, name='taxon-search'),
    re_path(r'^(?P<key>[0-9]+)/', taxonDetailView, name='taxon-detail'),
]

occurrence_url_patterns = [
    re_path(r'^search/$', occurrence_list_view_async, name='occurrence-search'),
    re_path(r'^download/$', OccurrenceDownloadView.as_view(), name='occurrence-download'),
]

# urls for download files
download_url_patterns = [
    re_path(r'^$', DownloadsListView.as_view(), name='my-downloads'),
    re_path(r'^request/(?P<download_id>[0-9]+)/$', get_download, name='my-download-file'),
]

# API urls
api_occurrence_url_patterns = [
    re_path(r'^search/$', occurrence_search_view, name='api-occurrence-search'),
    re_path(r'^count/$', occurrence_count, name='api-occurrence-count'),
    re_path(r'^grid/$', occurrence_grid, name='api-occurrence-grid'),
]

api_download_url_patterns = [
    re_path(r'^download/$', DownloadListCreateAPIView.as_view(), name='download-list'),
    re_path(r'^download/(?P<pk>[0-9]+)/$', DownloadRetrieveDestroyAPIView.as_view(), name='download-detail'),
]

# v1.0 API url patterns
api_v1_url_patterns = []
api_v1_url_patterns += router.urls
api_v1_url_patterns += api_download_url_patterns

# urls for API web services
api_url_patterns = [
    re_path(r'^db-statistics/$', database_statistics, name='db-statistics'),
    re_path(r'^occurrence/', include(api_occurrence_url_patterns)),
    re_path(r'^v1.0/', include((api_v1_url_patterns, 'data_manager'), namespace='v1.0')),
    re_path(r'^v1.0/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^v1.0/swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api-auth/', include('rest_framework.urls')),
]

all_url_patterns = [
    re_path(r'^', include('django.contrib.auth.urls')),
    re_path(r'^$', HomePageView.as_view(), name='home'),
    re_path(r'^haproxy/$', haproxy_view, name='haproxy'),
    re_path(r'^dataset/', include(dataset_url_patterns)),
    re_path(r'^occurrence/', include(occurrence_url_patterns)),
    re_path(r'^taxon/', include(taxon_url_patterns)),
    re_path(r'^download/', include(download_url_patterns)),
    re_path(r'^api/', include(api_url_patterns)),
    # footer pages
    re_path(r'^contact/$', ContactView.as_view(), name='contact'),
    re_path(r'^policy/$', PolicyView.as_view(), name='policy'),
    re_path(r'^data-source/$', DataSourceView.as_view(), name='data-source'),
    re_path(r'^help/$', HelpView.as_view(), name='help'),
    # authentication
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^login/', auth_views.LoginView.as_view(), name='login'),
    re_path(r'^register/$', register, name='register'),
    re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
            activate, name='activate'),
]

if settings.URL_PREFIX:
    urlpatterns = [
        re_path(settings.URL_PREFIX, include(all_url_patterns))
    ]
else:
    urlpatterns = all_url_patterns

urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# When using format_suffix_patterns, make sure to add the 'format' keyword argument to the corresponding views.
# only use this for the api urls
api_url_patterns = format_suffix_patterns(api_url_patterns)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
