"""Authenticated local administrative contract read; contains no provider URL."""
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.accounts.permissions import IsAdmin
from .provider_security import contract, Denied


@api_view(['GET'])
@permission_classes([IsAdmin])
def provider_security(request):
    if settings.DEBUG is not False: return Response({'error':'provider_security_unavailable'},status=403)
    try:
        result=contract(request.query_params.get('provider_key'))
        if request.query_params.get('epg_url_sha256')!=result['epg_url_sha256']: raise Denied()
        return Response(result)
    except Denied: return Response({'error':'provider_security_unavailable'},status=403)
