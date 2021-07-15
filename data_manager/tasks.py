# -*- coding: utf-8 -*-
from celery import shared_task
from celery.utils.log import get_task_logger
from data_manager.filters import OccurrenceFilter
from data_manager.helpers import create_download_file, get_dataset_queryset_from_form, \
    get_occurrence_queryset_from_form, write_file
from data_manager.models import GBIFOccurrence, Download
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = get_task_logger(__name__)

User = get_user_model()


class MailNotSent(Exception):
    pass


class CouldNotCreateDownload(Exception):
    pass


@shared_task
def debug_task():
    return 'Task accepted'


@shared_task(bind=True, name='tasks.prepare_download_file')
def prepare_download_file(self, download_id, download_link):
    """
    Generate download file asynchronously.
    :param self: this Task
    :param download_id: An integer that uniquely identify the Download instance.
    :param download_link: A string. The absolute uri to the Download's file.
    :return: A string. A UUID that identify this task.
    """
    task_id = self.request.id
    download = Download.objects.get(id=download_id)
    query_dict = download.get_query_dict()  # convert string to QueryDict
    queryset = OccurrenceFilter(query_dict, queryset=GBIFOccurrence.objects.all()).qs
    record_count = queryset.count()
    Download.objects.filter(id=download_id).update(record_count=record_count, task_id=task_id)
    try:
        write_file(queryset=queryset, field_names=settings.OCCURRENCE_FIELDS, download=download, prepare_download_id=task_id)
    except Exception as e:
        raise CouldNotCreateDownload(e)
    email_message = f'Hi {download.user.username}, your download is ready. Please go to {download_link} to download the ' \
                    f'file.\nThe download file will remain available online for ' \
                    f'{settings.DOWNLOAD_FILE_STORAGE_PERIOD} days.\n\nQuery: ' \
                    f'{download.query}\n\nThe biodiversity.aq team'
    send_mail(subject='[Do not reply] Your download is ready', message=email_message,
              from_email='noreply@biodiversity.aq', recipient_list=[download.user.email],
              auth_user='', fail_silently=False)
    return task_id


@shared_task(bind=True, name='tasks.prepare_download')
def prepare_download(self, model, download_link, user_id, download_id):
    """
    Generate download file from search results, notify user by sending email once download file is successfully
    generated.
    """
    task_id = self.request.id
    download = Download.objects.get(id=download_id)
    download_query_dict = download.get_query_dict()
    if model == 'Dataset':
        dataset_queryset, form = get_dataset_queryset_from_form(download_query_dict)
        occurrence_queryset = GBIFOccurrence.objects.filter(dataset__in=dataset_queryset)
    elif model == 'GBIFOccurrence':
        occurrence_queryset, form, latitude_range, longitude_range = \
            get_occurrence_queryset_from_form(download_query_dict)
    else:
        occurrence_queryset = GBIFOccurrence.objects.none()
    if occurrence_queryset.exists():
        user = User.objects.get(id=user_id)
        download.task_id = task_id
        download.record_count = occurrence_queryset.count()
        download.save()
        download = create_download_file(
            queryset=occurrence_queryset, field_names=settings.OCCURRENCE_FIELDS, download=download)
        email_message = f'Hi {user.username}, your download is ready. Please go to {download_link} to download the ' \
                    f'file.\nThe download file will remain available online for ' \
                    f'{settings.DOWNLOAD_FILE_STORAGE_PERIOD} days.\n\nQuery: ' \
                    f'{download.query}\n\nThe biodiversity.aq team'
        send_mail(subject='[Do not reply] Your download is ready', message=email_message,
                  from_email='noreply@biodiversity.aq', recipient_list=[download.user.email],
                  auth_user='', fail_silently=False)
        return task_id
    else:
        return
