from rest_framework import serializers
from rest_framework.serializers import ValidationError

from agents.models import Agent, UpdateFile


class ReadOnlyAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'title', 'api_ip', 'api_port', 'av_name', 'created_at']
        read_only_fields = ['id', 'title', 'api_ip', 'av_name', 'api_port',
                            'created_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['av_logo'] = None
        for item in Agent.av_names:
            if item['code'] == instance.av_name:
                representation['av_name_display'] = item.get('display')
                representation['av_logo'] = item.get('logo')
                break
        return representation


class AgentSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='agent-detail')
    scans_count = serializers.IntegerField(read_only=True)
    infected_count = serializers.IntegerField(read_only=True)
    clean_count = serializers.IntegerField(read_only=True)
    mysterious_count = serializers.IntegerField(read_only=True)
    avg_scan_time = serializers.FloatField(read_only=True)

    class Meta:
        model = Agent
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['av_logo'] = None
        for item in Agent.av_names:
            if item['code'] == instance.av_name:
                representation['av_name_display'] = item.get('display')
                representation['av_logo'] = item.get('logo')
                break
        return representation

    def validate_av_name(self, value):
        choices = [item['code'] for item in Agent.av_names]
        if value not in choices:
            raise ValidationError('Not a valid choice for "av_name"')
        return value

    def create(self, validated_data):
        active = validated_data.get('active')
        if not active:
            validated_data['status'] = None
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        active = validated_data.get('active')
        validated_data.pop('av_name', None)
        if active is not None and not active:
            validated_data['status'] = None
        instance = super().update(instance, validated_data)
        return instance


class UpdateFromDiskSerializer(serializers.Serializer):
    path = serializers.CharField()


class UpdateFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = UpdateFile
        fields = '__all__'