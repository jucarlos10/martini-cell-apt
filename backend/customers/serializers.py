from rest_framework import serializers

from .models import Client, ClientChangeHistory
from .validators import normalize_rut, validate_rut


class ClientSerializer(serializers.ModelSerializer):
    rut = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    document_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )

    phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )

    identification_type_display = serializers.CharField(
        source="get_identification_type_display",
        read_only=True,
    )

    identification_display = serializers.CharField(
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )
    updated_by_username = serializers.CharField(
        source="updated_by.username",
        read_only=True,
    )

    class Meta:
        model = Client
        fields = (
            "id",
            "identification_type",
            "identification_type_display",
            "rut",
            "document_number",
            "identification_display",
            "name",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
        )
        read_only_fields = (
            "id",
            "identification_type_display",
            "identification_display",
            "created_at",
            "updated_at",
            "created_by_username",
            "updated_by_username",
        )

    def validate_rut(self, value):
        if value in {None, ""}:
            return None

        rut = normalize_rut(value)

        validate_rut(rut)

        queryset = Client.objects.filter(rut=rut)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un cliente registrado con este RUT."
            )

        return rut

    def validate_document_number(self, value):
        return str(value or "").strip().upper()

    def validate(self, attrs):
        identification_type = attrs.get(
            "identification_type",
            getattr(
                self.instance,
                "identification_type",
                Client.IdentificationType.RUT,
            ),
        )

        rut = attrs.get(
            "rut",
            getattr(self.instance, "rut", None),
        )

        document_number = attrs.get(
            "document_number",
            getattr(self.instance, "document_number", ""),
        )

        phone = str(
            attrs.get(
                "phone",
                getattr(self.instance, "phone", ""),
            )
            or ""
        ).strip()

        email = str(
            attrs.get(
                "email",
                getattr(self.instance, "email", ""),
            )
            or ""
        ).strip()

        attrs["phone"] = phone

        if identification_type == Client.IdentificationType.RUT:
            if not rut:
                raise serializers.ValidationError(
                    {
                        "rut": (
                            "Ingresa el RUT del cliente o selecciona "
                            "otro tipo de identificación."
                        )
                    }
                )

            attrs["rut"] = rut
            attrs["document_number"] = ""

        elif identification_type in {
            Client.IdentificationType.PASSPORT,
            Client.IdentificationType.FOREIGN_DOCUMENT,
        }:
            document_number = str(
                document_number or ""
            ).strip().upper()

            if not document_number:
                raise serializers.ValidationError(
                    {
                        "document_number": (
                            "Ingresa el número del documento "
                            "seleccionado."
                        )
                    }
                )

            duplicate = Client.objects.filter(
                identification_type=identification_type,
                document_number__iexact=document_number,
            )

            if self.instance:
                duplicate = duplicate.exclude(
                    pk=self.instance.pk
                )

            if duplicate.exists():
                raise serializers.ValidationError(
                    {
                        "document_number": (
                            "Ya existe un cliente registrado con "
                            "este documento."
                        )
                    }
                )

            attrs["rut"] = None
            attrs["document_number"] = document_number

        else:
            attrs["rut"] = None
            attrs["document_number"] = ""

        if not phone and not email:
            raise serializers.ValidationError(
                {
                    "contact": (
                        "Ingresa al menos un teléfono o un correo "
                        "electrónico para contactar al cliente."
                    )
                }
            )

        return attrs


class ClientChangeHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
    )

    class Meta:
        model = ClientChangeHistory
        fields = (
            "id",
            "changed_at",
            "changed_by_username",
            "changes",
        )
        read_only_fields = fields
