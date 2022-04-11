import os

from kombu.exceptions import OperationalError as KombuOperationError
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from agents.serializers import ReadOnlyAgentSerializer
from agents.models import Agent
from scans.models.file import File, FileInfo
from scans.models.scan import Scan, ScanReport
from scans.models.session import Session
from core.utils.files import discover_mimetype
from core.models.system import System


class ReadOnlyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('username', )


class CleanupSerializer(serializers.Serializer):
    days_older_than = serializers.IntegerField()


class SessionSerializer(serializers.ModelSerializer):
    files_count = serializers.IntegerField(read_only=True)
    owner_username = serializers.CharField(read_only=True, source='username')
    status = serializers.CharField(read_only=True, source='progress')
    session_id = serializers.CharField(read_only=True, source='pk')
    started_at = serializers.DateTimeField(read_only=True, source='created_at')

    class Meta:
        model = Session
        fields = '__all__'


class ReadOnlyFileSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()
    owner = ReadOnlyUserSerializer(read_only=True, source='user')
    scan_progress = serializers.FloatField(read_only=True, source='progress')
    session_id = serializers.IntegerField(read_only=True, source='session.pk')
    size = serializers.FloatField(read_only=True, source='info.size')
    md5 = serializers.CharField(read_only=True, source='info.md5')
    sha1 = serializers.CharField(read_only=True, source='info.sha1')
    sha256 = serializers.CharField(read_only=True, source='info.sha256')
    ext_match = serializers.BooleanField(read_only=True,
                                         source='info.ext_match')
    extension = serializers.CharField(read_only=True, source='info.extension')
    mimetype = serializers.CharField(read_only=True, source='info.mimetype')

    class Meta:
        model = File
        fields = '__all__'

    def get_filename(self, obj):
        try:
            return os.path.split(obj.file.path)[-1]
        except:
            return ''


class FileSerializer(serializers.ModelSerializer):
    scan = serializers.BooleanField(write_only=True)
    filename = serializers.SerializerMethodField()
    owner = ReadOnlyUserSerializer(read_only=True, source='user')
    scan_progress = serializers.FloatField(read_only=True, source='progress')
    extract = serializers.BooleanField(write_only=True, default=False)
    agents = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.filter(active=True), write_only=True, many=True,
        required=False
    )
    extracted = serializers.SerializerMethodField()
    session_id = serializers.IntegerField(read_only=True, source='session.pk')
    size = serializers.FloatField(read_only=True, source='info.size')
    md5 = serializers.CharField(read_only=True, source='info.md5')
    sha1 = serializers.CharField(read_only=True, source='info.sha1')
    sha256 = serializers.CharField(read_only=True, source='info.sha256')
    ext_match = serializers.BooleanField(read_only=True, source='info.ext_match')
    extension = serializers.CharField(read_only=True, source='info.extension')
    mimetype = serializers.CharField(read_only=True, source='info.mimetype')

    class Meta:
        model = File
        fields = '__all__'
        read_only_fields = ['username', 'display_name', 'notes', 'status',
                            'deleted', 'valid']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation.get('parent'):
            representation['parent'] = ReadOnlyFileSerializer(instance.parent).data
        return representation

    def get_filename(self, obj):
        try:
            return os.path.split(obj.file.path)[-1]
        except:
            return ''

    def get_extracted(self, obj):
        return obj.children.exists()

    def validate(self, data):
        file = data.get('file')

        if file:
            settings = System.get_settings()

            max_file_size = settings['max_file_size']
            if max_file_size and not file.size <= max_file_size:
                    msg = _('The uploaded file size exceeded {size}.')
                    raise ValidationError(msg.format(size=max_file_size))

            allowed_mimetypes = settings['mimetypes']
            mimetype = discover_mimetype(file)
            if allowed_mimetypes and mimetype not in allowed_mimetypes:
                    msg = _('The Uploaded file mimetype {mimetype} is not valid.')
                    raise ValidationError(msg.format(mimetype=mimetype))

            data['size'] = file.size
            data['mimetype'] = mimetype

        return data

    def create(self, validated_data):
        file = validated_data.get('file')
        scan = validated_data.pop('scan')
        agents = validated_data.pop('agents', None)
        extract = validated_data.pop('extract')
        extract_settings = System.get_settings()['extract']
        if extract_settings is not None:
            extract = extract_settings

        user = self.context['request'].user

        if not isinstance(user, get_user_model()):
            user = None

        session = Session.objects.create()

        size = validated_data.pop('size')
        mimetype = validated_data.pop('mimetype')
        info = FileInfo.objects.create(size=size, mimetype=mimetype)
        instance = File.objects.create(
            user=user, session=session, info=info, valid=True,
            display_name=file.name.split('/')[-1], **validated_data
        )
        Session.objects.filter(pk=session.pk).update(
            total=1,
            counter=1,
            analyze_progress=100
        )
        # celery_app.control.add_consumer(queue=session_id, reply=True)

        instance.set_file_info()
        if scan:
            instance.scan(extract=extract, agents=agents)

        elif extract:
            instance.extract()

        return instance

    def update(self, instance, validated_data):
        agents = validated_data.get('agents')
        extract_settings = System.get_settings()['extract']
        if extract_settings is None:
            extract = validated_data.get('extract')
        else:
            extract = extract_settings

        # celery_app.control.add_consumer(queue=instance.session_id, reply=True)
        new = instance
        new.pk = None
        session = Session.objects.create()
        new.session = session
        new.save()
        if extract:
            for child in instance.children.all():
                new_child = child
                new_child.pk = None
                new_child.session = session
                new_child.parent = new
                new_child.save()
        Session.objects.filter(pk=session.pk).update(
            total=1,
            counter=1,
            analyze_progress=100
        )
        new.scan(extract=extract, agents=agents)

        return instance


class FromUrlSerializer(serializers.Serializer):
    scan = serializers.BooleanField(write_only=True)
    url = serializers.URLField(write_only=True)
    save_as = serializers.CharField(write_only=True, max_length=256,
                                    required=False)
    extract = serializers.BooleanField(write_only=True, default=False)
    agents = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.filter(active=True), write_only=True, many=True,
        required=False
    )

    def create(self, validated_data):
        scan = validated_data.pop('scan')
        url = validated_data.pop('url')
        save_as = validated_data.pop('save_as', None)
        agents = validated_data.pop('agents', None)
        extract_settings = System.get_settings()['extract']
        if extract_settings is None:
            extract = validated_data.get('extract')
        else:
            extract = extract_settings

        user = self.context['request'].user
        if not isinstance(user, get_user_model()):
            user = None

        try:
            session = File.objects.create_from_url(url, save_as=save_as,
                                                   scan=scan,
                                                   extract=extract,
                                                   owner=user,
                                                   agents=agents)
        except KombuOperationError as e:
            raise ValidationError(str(e))

        return session


class FromPathSerializer(serializers.Serializer):
    scan = serializers.BooleanField(write_only=True)
    file = serializers.CharField(write_only=True)
    extract = serializers.BooleanField(write_only=True, default=False)
    agents = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.filter(active=True), write_only=True, many=True,
        required=False
    )

    def create(self, validated_data):
        file = validated_data.get('file')
        scan = validated_data.pop('scan')
        agents = validated_data.pop('agents', None)
        extract_settings = System.get_settings()['extract']
        if extract_settings is None:
            extract = validated_data.get('extract')
        else:
            extract = extract_settings

        user = self.context['request'].user
        if not isinstance(user, get_user_model()):
            user = None

        try:
            session = File.objects.create_from_path(file, scan=scan,
                                                    extract=extract,
                                                    owner=user,
                                                    agents=agents)
        except KombuOperationError as e:
            raise ValidationError(str(e))

        return session


class FromDiskSerializer(serializers.Serializer):
    paths = serializers.ListField(child=serializers.CharField())
    scan = serializers.BooleanField(write_only=True)
    extract = serializers.BooleanField(write_only=True, default=False)
    agents = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.filter(active=True), write_only=True, many=True,
        required=False
    )

    def create(self, validated_data):
        paths = validated_data.get('paths')
        scan = validated_data.get('scan')
        agents = validated_data.pop('agents', None)
        extract_settings = System.get_settings()['extract']
        if extract_settings is None:
            extract = validated_data.get('extract')
        else:
            extract = extract_settings

        user = self.context['request'].user
        if not isinstance(user, get_user_model()):
            user = None

        try:
            session = File.objects.bulk_create_from_disk(paths, scan=scan,
                                                         extract=extract,
                                                         owner=user,
                                                         agents=agents)
        except KombuOperationError as e:
            raise ValidationError(str(e))

        return session


class CopySerializer(serializers.Serializer):
    path = serializers.CharField()


class FtpSerializer(serializers.Serializer):
    path = serializers.CharField()


class ScanSerializer(serializers.ModelSerializer):
    agent = ReadOnlyAgentSerializer(read_only=True)
    av = serializers.SerializerMethodField()
    scan_status_code = serializers.IntegerField(source='status_code',
                                                read_only=True)
    file = ReadOnlyFileSerializer(read_only=True)

    class Meta:
        model = Scan
        exclude = ('status_code', )

    def get_av(self, obj):
        for av in Agent.av_names:
            if av['code'] == obj.av_name:
                return av


class ScanReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanReport
        fields = '__all__'
