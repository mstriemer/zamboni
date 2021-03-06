import hashlib

from django import http
from django.shortcuts import get_object_or_404
from django.views.decorators.http import etag

import commonware.log

import mkt
from mkt.constants import MANIFEST_CONTENT_TYPE
from mkt.site.decorators import allow_cross_site_request
from mkt.webapps.decorators import app_view_factory
from mkt.webapps.models import Webapp


log = commonware.log.getLogger('z.detail')


addon_all_view = app_view_factory(qs=Webapp.objects.all)


@allow_cross_site_request
def manifest(request, uuid):
    """Returns the "mini" manifest for packaged apps.

    If not a packaged app, returns a 404.

    """
    addon = get_object_or_404(Webapp, guid=uuid, is_packaged=True)
    is_avail = addon.status in [mkt.STATUS_PUBLIC, mkt.STATUS_UNLISTED,
                                mkt.STATUS_BLOCKED]
    is_owner = addon.authors.filter(pk=request.user.pk).exists()
    is_owner_avail = addon.status == mkt.STATUS_APPROVED
    package_etag = hashlib.sha256()

    if (addon.is_packaged and
        not addon.disabled_by_user and
            (is_avail or (is_owner_avail and is_owner))):

        manifest_content = addon.get_cached_manifest()
        package_etag.update(manifest_content)

        if addon.is_packaged:
            # Update the hash with the content of the package itself.
            package_file = addon.get_latest_file()
            if package_file:
                package_etag.update(package_file.hash)

        manifest_etag = package_etag.hexdigest()

        @etag(lambda r, a: manifest_etag)
        def _inner_view(request, addon):
            response = http.HttpResponse(manifest_content,
                                         content_type=MANIFEST_CONTENT_TYPE)
            return response

        return _inner_view(request, addon)

    else:
        raise http.Http404
