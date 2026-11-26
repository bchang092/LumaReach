"""Expiring, signed invitations for source-grounded tag review. No public writes."""
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.http import Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from lifeline_core.repository import directory
from .models import ResourceTagReview


def make_review_token(resource_id):
    return signing.dumps({'resource_id':resource_id},salt='resource-tag-review')


@never_cache
@require_http_methods(['GET','POST'])
def review_resource(request, token):
    try:
        rid=signing.loads(token,salt='resource-tag-review',max_age=7*86400)['resource_id']
    except (signing.BadSignature,KeyError): raise PermissionDenied('Review invitation expired or invalid.')
    repo=directory(); resource=repo.get(rid)
    if not resource or 'record_sha256' not in resource: raise Http404
    error=''; saved=False
    if request.method=='POST':
        tag=request.POST.get('tag',''); evidence=request.POST.get('evidence','').strip()
        if tag not in repo.allowed_needs or len(evidence)<8 or evidence not in resource['description']:
            error='Choose a service tag and copy supporting words exactly from the description (at least 8 characters).'
        else:
            ResourceTagReview.objects.get_or_create(resource_id=rid,proposed_tag=tag,evidence=evidence,record_sha256=resource['record_sha256'])
            saved=True
    return render(request,'resource_review.html',{'resource':resource,'tags':sorted(repo.allowed_needs),'error':error,'saved':saved})
