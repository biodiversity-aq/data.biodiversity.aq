# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache.utils import make_template_fragment_key
from django.core.mail import EmailMessage
from django.db.models import Count, Sum
from django.http import HttpResponse, Http404
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import DetailView
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from data_manager.forms import *
from data_manager.models import *
from data_manager.helpers import get_dataset_queryset_from_form, get_occurrence_queryset_from_form, \
    create_download_file
from data_manager.tasks import prepare_download

from data_manager.tokens import account_activation_token
from collections import defaultdict
from datetime import datetime, timedelta
from pygbif import species, registry, occurrences
import logging
import re


# LOGGING CONFIGURATION
logger = logging.getLogger(__name__)


def query_dict_to_dict(query_dict):
    """
    Convert QueryDict to a dictionary with list values.
    :param query_dict: A QueryDict instance
    :return: a dictionary with list
    """
    d = dict()
    for key in query_dict:
        d[key] = query_dict.getlist(key)
    return d


class DatasetDownloadView(View):
    """Manages Datasets downloads"""
    form_class = DatasetFilterForm

    @method_decorator(login_required)
    def async_download(self, request):
        """
        Asynchronous download - download will be put into queue (Redis)
        Login required. Celery will be used to execute the tasks.
        """
        response = DatasetListView.as_view()(request)
        # !! Passing QuerySet to celery task will raise EncodeError: Object of type QuerySet is not JSON serializable
        dataset_qs, form = get_dataset_queryset_from_form(request.GET)
        qs = GBIFOccurrence.objects.filter(dataset__in=dataset_qs)
        record_count = qs.count()
        if record_count == 0:
            if dataset_qs.count() > 0:
                messages.error(request, message='Sorry, download of metadata-only datasets is currently not supported')
            else:
                messages.error(request, message='Nothing to download')
        elif 0 < record_count < settings.MAX_OCCURRENCE_COUNT_PERMITTED:
            user = User.objects.get(id=request.user.id)
            download_query = query_dict_to_dict(query_dict=request.GET)
            download = Download.objects.create(user=user, query=download_query)
            download_link = request.build_absolute_uri(reverse('my-download-file', args=(download.id,)))
            prepare_download.apply_async(('Dataset', download_link, user.id, download.id), retry=True)
            messages.info(request, 'An email will be sent to you once the download is ready.')
        elif record_count > settings.MAX_OCCURRENCE_COUNT_PERMITTED:
            messages.error(request, message='Download abort. File size too large')
        return response

    def get(self, request, *args, **kwargs):
        return self.async_download(request)


class OccurrenceDownloadView(View):
    """Manages occurrence downloads"""
    form_class = OccurrenceFilterForm

    @method_decorator(login_required)
    def async_download(self, request, *args, **kwargs):
        """
        Asynchronous download - download will be put into queue (Redis)
        Login required. Celery will be used to execute the tasks.
        """
        queryset, form, latitude_range, longitude_range = get_occurrence_queryset_from_form(request.GET)
        record_count = queryset.count()
        response = occurrence_list_view_async(request)
        if record_count == 0:
            messages.error(request, message='Nothing to download')
        elif 0 < record_count < settings.MAX_OCCURRENCE_COUNT_PERMITTED:
            user = User.objects.get(id=request.user.id)
            download_query = query_dict_to_dict(query_dict=request.GET)
            download = Download.objects.create(user=user, query=download_query)
            download_link = request.build_absolute_uri(reverse('my-download-file', args=(download.id, )))
            prepare_download.apply_async(('GBIFOccurrence', download_link, user.id, download.id), retry=True)
            messages.info(request, 'An email will be sent to you once the download is ready.')
        elif record_count > settings.MAX_OCCURRENCE_COUNT_PERMITTED:
            messages.error(request, message='Download abort. File size too large')
        return response

    def get(self, request):
        """
        Determine if synchronous/asynchronous download should be used based on settings.USE_BACKGROUND_DOWNLOADS.
        """
        return self.async_download(request)


class DatasetListView(ListView):
    """
    Display list of datasets based on search field in home page.
    If search field is empty, all datasets will be listed.
    """
    model = Dataset
    template_name = 'dataset-list.html'
    paginate_by = 20

    def get_queryset(self):
        qs, self.form = get_dataset_queryset_from_form(self.request.GET)
        return qs.prefetch_related('data_type', 'project', 'publisher')

    def get_context_data(self, **kwargs):
        context = super(DatasetListView, self).get_context_data(**kwargs)
        context['form'] = self.form
        return context


class DatasetDetailView(DetailView):
    """
    Display detail of datasethttps://git.bebif.be/users/sign_in
    url based on dataset/dataset.id
    return 404 when id not found
    """
    model = Dataset
    template_name = 'dataset-detail.html'
    context_object_name = 'dataset'

    def get_context_data(self, **kwargs):

        context = super(DatasetDetailView, self).get_context_data(**kwargs)
        try:
            context['doi'] = self.object.doi
        except TypeError:
            context['doi'] = ''
            pass
        except IndexError:
            context['doi'] = ''
            pass
        except AttributeError:
            context['doi'] = ''
            pass
        try:
            context['contacts'] = Person.objects.filter(personTypeRole__dataset_id=self.object.id, personTypeRole__person_type='contact')
        except TypeError:
            context['contact'] = None
            pass
        except AttributeError:
            context['contacts'] = None
            pass
        try:
            context['alternate_links'] = [link for link in self.object.alternate_identifiers if link.startswith('http')]
        except TypeError:
            context['alternate_links'] = None
            pass
        except AttributeError:
            context['alternate_links'] = None
            pass
        try:
            context['citation'] = self.object.citation.split(' accessed via GBIF', 1)[0]
        except TypeError:
            context['citation'] = None
            pass
        except AttributeError:
            context['citation'] = None
            pass
        context['keywords'] = defaultdict(list)
        for keyword in Keyword.objects.filter(dataset__id=self.object.id):
            try:
                context['keywords'][keyword.thesaurus].append(keyword.keyword)
            except AttributeError:
                pass
        # The template variable resolution algorithm in Django will attempt to resolve
        # new_data.items as new_data['items'] first, which resolves to an empty list when using
        # defaultdict(list). To disable the defaulting to an empty list and have Django fail on new_data['items']
        # then continue the resolution attempts until calling new_data.items(),
        # the default_factory attribute of defaultdict can be set to None.
        context['keywords'].default_factory = None
        context['contributors'] = Person.objects.filter(personTypeRole__dataset_id=self.object.id).annotate(field_count=Count('personTypeRole__person_type')).order_by('-field_count')
        context['organizations'] = PersonTypeRole.objects.filter(dataset_id=self.object.id).values_list('person__full_name', 'organization').distinct()
        context['GEOSERVER_HOST'] = settings.GEOSERVER_HOST
        context['has_grid'] = HexGrid.objects.filter(GBIFOccurrence__dataset_id=self.object.id).exists()
        return context


def occurrence_list_view_async(request):
    """
    List occurrence search results in table asynchronously
    :param request: HTTP GET request
    :return: a TemplateResponse
    """
    context = dict()
    # use url as cache key for {% cache 2592000 formcache key %}
    # to avoid the form from re-querying for form.fields['basis_of_record'].queryset & form.fields['dataset'].queryset
    # for every page. See more: https://docs.djangoproject.com/en/1.11/topics/cache/#template-fragment-caching
    cache_url = re.sub(r'\&page\=\d+', '', request.META.get('QUERY_STRING'))
    key = make_template_fragment_key('formcache', cache_url)
    qs, form, latitude_range, longitude_range = get_occurrence_queryset_from_form(request.GET)
    context['form'] = form
    context['key'] = key
    context['GEOSERVER_HOST'] = settings.GEOSERVER_HOST
    response = TemplateResponse(request, 'occurrence-list-async.html', context)
    return response


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        """
        Display statistics from database at home page
        """
        all_datasets = Dataset.objects.all().prefetch_related('data_type')

        context = super(HomePageView, self).get_context_data(**kwargs)
        context['total_datasets'] = all_datasets.count()
        context['occurrence_datasets_count'] = all_datasets.filter(data_type__data_type='Occurrence').count()
        context['checklists_count'] = all_datasets.filter(data_type__data_type='Checklist').count()
        context['event_datasets_count'] = all_datasets.filter(data_type__data_type='Sampling Event').count()
        context['metadata_datasets_count'] = all_datasets.filter(data_type__data_type='Metadata').count()
        context['total_occurrences'] = all_datasets.aggregate(Sum('filtered_record_count'))['filtered_record_count__sum']
        context['GEOSERVER_HOST'] = settings.GEOSERVER_HOST

        return context


def taxonListView(request):
    """Render queryset of Taxon search into template
    :param request: HTTP GET request
    :return: TemplateResponse with context of taxon search
    """
    # initialise variables
    r = ''
    results = None
    # get offset parameters from GET request
    offset = int(request.GET.get('offset', 0))
    if offset < 0:
        logger.debug('negative offset not supported, offset is set to 0')
        offset = 0
        previous = 0
    elif offset >= 20:
        previous = offset - 20 + 1
    else:
        previous = 0
    # form
    form = TaxonSearchForm(request.GET, initial=request.GET)
    source_title_dict = dict()
    if form.is_valid():  # form only have cleaned_data attribute after is_valid() is called
        q = form.cleaned_data.get('q', '')
        backbone = form.cleaned_data.get('backbone', '')
        # datasetKey points to GBIF taxonomic backbone and WoRMS
        if backbone:
            r = species.name_lookup(q=q, limit=20, offset=offset, datasetKey=backbone)
        else:
            r = species.name_lookup(q=q, limit=20, offset=offset, datasetKey=['2d59e5db-57ad-41ff-97d6-11f5fb264527', 'd7dddbf4-2cf0-4f39-9b2a-bb099caae36c'])  # if q is '', API returns all taxa
        results = r.get('results', None)
        if results:
            for result in results:
                source_uuid = result.get('datasetKey', '')
                dataset_title = registry.datasets(uuid=source_uuid).get('title', '')
                source_title_dict[source_uuid] = dataset_title
                key = result.get('key')
                result['higherClassificationMap'] = species.name_usage(key=key, data='parents')
    # context
    context = dict()
    context['form'] = form
    context['results'] = results
    context['results_count'] = r.get('count', None)
    context['source_title_dict'] = source_title_dict
    context['higher_taxa_rank'] = ['KINGDOM', 'PHYLUM', 'CLASS', 'ORDER', 'FAMILY', 'GENUS', 'SPECIES']
    # context for pagination
    context['previous'] = previous
    context['offset'] = offset
    context['end_of_records'] = r.get('endOfRecords', None)
    response = TemplateResponse(request, 'taxon-list.html', context)
    return response


def taxonDetailView(request, key):
    """Render Taxon with specific key into TemplateResponse
    :param request: HTTP GET request
    :param key: GBIF taxonKey of specific taxon
    :return: TemplateResponse with context of specific taxon
    """
    taxon_result = species.name_usage(key=key)
    source_uuid = taxon_result.get('datasetKey')
    references = taxon_result.get('references', '')
    gbif_taxon_key = taxon_result.get('nubKey', '')  # nubKey = key of the taxon in GBIF Taxonomy Backbone
    media_links = None
    # MEDIA
    if gbif_taxon_key:
        gbif_occ = occurrences.search(country='AQ', taxonKey=gbif_taxon_key, mediatype="stillImage", limit=10).get('results', None)
        media_links = set()
        if gbif_occ:
            for record in gbif_occ:
                media_list = record.get('media', '')
                for media in media_list:
                    identifier = media.get('identifier', '')
                    if len(media_links) != 10:
                        media_links.add(identifier)
    # PARENTS
    parents_request = species.name_usage(key=key, data='parents')  # return list of dicts
    # DIRECT CHILDREN
    children_request = species.name_usage(key=key, data='children', limit=20)
    children = children_request.get('results', None)
    end_of_records = children_request.get('endOfRecords', True)
    # AQ OCC
    rank = taxon_result.get('rank', '')
    if rank in ['KINGDOM', 'PHYLUM', 'CLASS', 'ORDER', 'FAMILY', 'GENUS', 'SUBGENUS', 'SPECIES']:
        rank = rank.lower()
        field = '{}Key'.format(rank)
        kwargs = {'{}'.format(field): key}
        has_occurrence = GBIFOccurrence.objects.filter(**kwargs).exists()
    else:
        has_occurrence = False
    # CONTEXT
    context = dict()
    context['taxon'] = taxon_result
    context['parents'] = parents_request
    context['references'] = references
    context['dataset'] = registry.datasets(uuid=source_uuid)  # dataset title of the taxonomic backbone
    context['media'] = media_links
    context['children'] = children
    context['has_occurrence'] = has_occurrence
    context['end_of_records'] = end_of_records
    context['GEOSERVER_HOST'] = settings.GEOSERVER_HOST
    response = TemplateResponse(request, 'taxon-detail.html', context)
    return response


class ContactView(TemplateView):
    template_name = 'contact.html'


class PolicyView(TemplateView):
    template_name = 'policies.html'


class HelpView(TemplateView):
    template_name = 'help.html'


class DataSourceView(TemplateView):
    template_name = 'data-source.html'


def register(request):
    """
    Account registration view
    Username is set to be EmailField and the value of User.email is set to be the same as username.
    :param request: Http request
    :return: registration page with form or redirect to home page with successful message
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.email = user.username  # set email as the username. username needs to be email.
            user.save()
            current_site = get_current_site(request)
            absolute_uri = request.build_absolute_uri(reverse('activate', args=(urlsafe_base64_encode(force_bytes(user.pk)), account_activation_token.make_token(user))))
            message = render_to_string('registration/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'absolute_uri': absolute_uri
            })
            mail_subject = 'Activate your data.biodiversity.aq account'
            to_email = user.email
            try:
                email = EmailMessage(mail_subject, message, to=[to_email])
                email.send()
            except Exception as e:
                # delete user from db if email is not sent
                # otherwise user cannot re-register because username is already exists in db
                User.objects.filter(username=user.username).delete()
                logger.error(e)
                messages.error(request, 'Error message: {}. Please try again.'.format(e))
                return render(request, 'registration/register.html', {'form': form})
            # place dismissable message on home page after redirection
            messages.success(request, 'Thank you. Please confirm your email address to complete the registration.')
            return redirect('home')
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def activate(request, uidb64, token):
    """Activate a new user account with token from confirmation email.
    :param request:
    :param uidb64: user's ID encoded in base 64
    :param token: token to check if the link is valid
    :return: redirect to home page
    """
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'Thank you for your email confirmation!')
    else:
        messages.error(request, 'Activation link is invalid!')
    return redirect('home')


class DownloadsListView(LoginRequiredMixin, ListView):
    """List metadata of downloads of last 7 days of a user when logged in."""
    model = Download
    template_name = 'my-downloads.html'
    paginate_by = 20

    def get_queryset(self):
        return Download.objects.filter(user=self.request.user, created_at__gt=datetime.now() - timedelta(days=7))


@login_required
def get_download(request, download_id):
    """Link to download file. Login required.
    :param request: HTTP GET request
    :param download_id: ID of the download file
    :return: HTTP Response, zipped download file
    """
    download = Download.objects.get(pk=download_id)
    if download.user != request.user:
        raise Http404
    response = HttpResponse(download.file, content_type='application/zip')
    filename = download.task_id + '.zip'
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response


def dataset_activity(request, pk):
    """Dataset activity metadata such as number of times it was being downloaded
    :param request: HTTP GET request
    :param pk: ID of a dataset
    :return: Template response which populates the template dataset-activity.html
    """
    downloads = Download.objects.filter(dataset=pk)
    total_downloads = downloads.count()
    context = dict()
    context['dataset'] = Dataset.objects.get(pk=pk)
    context['total_downloads'] = total_downloads
    return TemplateResponse(request, 'dataset-activity.html', context=context)


def haproxy_view(request):
    """Haproxy view
    :param request: Http request
    :return: plain text string 'ok'
    """
    content = 'ok'
    response = HttpResponse(content, content_type='text/plain')
    return response
