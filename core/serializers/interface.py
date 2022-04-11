from rest_framework import serializers


class AddressSerializer(serializers.Serializer):
    address = serializers.CharField()
    netmask = serializers.CharField(allow_null=True)
    broadcast = serializers.CharField(allow_null=True)
    ptp = serializers.BooleanField(allow_null=True)


class AddressListSerializer(serializers.Serializer):
    AF_INET = serializers.ListField(child=AddressSerializer(), required=False,
                                    allow_null=True, allow_empty=True)
    AF_INET6 = serializers.ListField(child=AddressSerializer(), required=False,
                                     allow_null=True, allow_empty=True)
    AF_PACKET = serializers.ListField(child=AddressSerializer(),
                                      required=False, allow_null=True,
                                      allow_empty=True)


class InterfaceSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(('up', 'UP'), ('down', 'DOWN')))
    addresses = AddressListSerializer()
    gateway4 = serializers.CharField(required=False, allow_null=True)


class InterfaceListSerializer(serializers.Serializer):
    content = serializers.DictField(child=InterfaceSerializer())