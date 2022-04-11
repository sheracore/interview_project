import os

from django.db.models import Count, Q, F, Avg
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from core.views import ServerViewSet
from core.utils.files import is_archive_file
from agents.models import Agent, UpdateFile
from agents.serializers import AgentSerializer, UpdateFromDiskSerializer, UpdateFileSerializer
from agents.permissions import AgentPermissions, UpdateFilePermissions
from agents.tasks import perform_update
from django.core.files import File as FileWrapper
from django.db import transaction

from rest_framework.viewsets import ModelViewSet


class AgentViewSet(ServerViewSet):
    queryset = Agent.objects.order_by('av_name')
    serializer_class = AgentSerializer
    permission_classes = [AgentPermissions]
    filter_fields = ('title', 'api_ip', 'active')
    # ordering_fields = ('title', 'active', 'created_at', 'modified_at',
    #                    'av_name')
    search_fields = ('title', 'api_ip', 'av_name')

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in {'list', 'retrieve'}:
            qs = qs.annotate(
                avg_scan_time=Avg('scans__scan_time'),
                scans_count=Count('scans'),
                infected_count=Count('scans',
                                     filter=Q(scans__infected_num__gt=0)),
                clean_count=Count('scans', filter=Q(scans__infected_num=0)),
                mysterious_count=F('scans_count') - (
                            F('infected_count') + F('clean_count')))
        return qs

    def get_serializer_class(self):
        if self.action == 'update_from_disk':
            return UpdateFromDiskSerializer
        if self.action == 'update_from_upload':
            return UpdateFileSerializer
        return super().get_serializer_class()

    # def perform_destroy(self, instance):
    #     with transaction.atomic():
    #         if instance.pt:
    #             PeriodicTask.objects.filter(pk=instance.pt.pk).delete()
    #         instance.delete()

    @action(methods=['get'], detail=True, url_path='sys/info')
    def sys_info(self, request, pk=None):
        instance = self.get_object()
        try:
            sys_info = instance.get_sys_info()
            return Response(sys_info, status.HTTP_200_OK)

        except ModuleNotFoundError as e:
            return Response({'detail': str(e)},
                            status=status.HTTP_404_NOT_FOUND)

        except (TimeoutError, OSError, EOFError) as e:
            return Response({'detail': f'Timout Error: {str(e)}'},
                            status=499)

    @action(methods=['get'], detail=False)
    def avs(self, request):
        return Response({'results': Agent.av_names}, status.HTTP_200_OK)

    @action(methods=['get'], detail=False)
    def stats(self, request):
        return Response({}, status.HTTP_200_OK)

    @action(methods=['patch'], detail=True, url_path='update/disk')
    def update_from_disk(self, request, pk=None):
        self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_path = serializer.validated_data['path']
        if not os.path.exists(file_path):
            raise ValidationError('invalid file path')
        if is_archive_file(file_path):
            with transaction.atomic():
                agent = Agent.objects.filter(pk=pk,
                                             updating=False).select_for_update().first()
                if not agent:
                    raise ValidationError('Agent is already in update process')
                agent.updating = True
                agent.save()
                with open(file_path, 'rb') as f:
                    f = FileWrapper(f)
                    instance = UpdateFile.objects.create(
                        file=f,
                        display_name=os.path.split(file_path)[-1],
                        agent=agent
                    )
                    self.perform_async(perform_update.si(
                        updatefile_id=instance.pk
                    ))

                return Response(UpdateFileSerializer(instance).data,
                                status.HTTP_200_OK)
        else:
            raise ValidationError('Not an archive type')

    @action(methods=['patch'], detail=True, url_path='update/upload',
            serializer_class=UpdateFileSerializer)
    def update_from_upload(self, request, pk=None):
        self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            agent = Agent.objects.filter(pk=pk, updating=False).select_for_update().first()
            if not agent:
                raise ValidationError('Agent is already in update process')
            agent.updating = True
            agent.save()
            instance = UpdateFile.objects.create(
                **serializer.validated_data,
                display_name=serializer.validated_data['file'].name.split('/')[-1],
                agent=agent
            )

            if is_archive_file(instance.file.path):
                self.perform_async(perform_update.si(instance.pk))
                return Response(data=UpdateFileSerializer(instance).data,
                                status=status.HTTP_200_OK)
            else:
                raise ValidationError('Not an archive type')


class UpdateFileViewSet(ModelViewSet):
    """
    Crud for UpdateFile model
    """
    queryset = UpdateFile.objects.all().order_by('-created_at')
    serializer_class = UpdateFileSerializer
    filter_fields = ('agent',)
    permission_classes = [UpdateFilePermissions]
