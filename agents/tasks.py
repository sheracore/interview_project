from celery import shared_task

from agents.models import Agent, UpdateFile
from agents.exceptions import AVException


@shared_task(name='agents.tasks.perform_update')
def perform_update(updatefile_id):
    instance = UpdateFile.objects.get(pk=updatefile_id)

    try:
        if instance.file:
            try:
                instance.agent.av.update(instance.file.path)
                instance.update(status_code=200)
            except ModuleNotFoundError as e:
                instance.update(status_code=404,
                                error=str(e))
                raise e
            except AVException as e:
                instance.update(status_code=498,
                                error=str(e))
                raise e
            except (TimeoutError, OSError, EOFError) as e:
                instance.update(status_code=499,
                                error=str(e))
                raise e
        else:
            instance.update(status_code=404,
                            error='Source file does not exist')
    finally:
        Agent.objects.filter(pk=instance.agent.pk).update(
            updating=False)

