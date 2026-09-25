from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .indicator_services import calculate_operational_indicators


class OperationalIndicatorsView(APIView):
    """
    HU-16 - CA-01.

    Permite consultar los indicadores operacionales
    correspondientes a un período determinado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in {"ADMIN", "TECH"}:
            return Response(
                {
                    "detail": (
                        "No tienes permiso para consultar "
                        "los indicadores operacionales."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        start_value = request.query_params.get("start")
        end_value = request.query_params.get("end")

        if not start_value or not end_value:
            return Response(
                {
                    "detail": (
                        "Debes indicar las fechas start y end "
                        "en formato YYYY-MM-DD."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date = parse_date(start_value)
        end_date = parse_date(end_value)

        if start_date is None or end_date is None:
            return Response(
                {
                    "detail": (
                        "Las fechas deben tener el formato "
                        "YYYY-MM-DD."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start_date > end_date:
            return Response(
                {
                    "detail": (
                        "La fecha inicial no puede ser posterior "
                        "a la fecha final."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = calculate_operational_indicators(
            start_date=start_date,
            end_date=end_date,
        )

        return Response(result)