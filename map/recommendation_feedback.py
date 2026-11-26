from lifeline_core.schemas import FeedbackInput
from lifeline_core.repository import directory
from .models import RecommendationFeedback


def submit_feedback(resource_id, helpful, comment=None):
    data=FeedbackInput(resource_id=resource_id,helpful=helpful,comment=comment)
    if directory().get(data.resource_id) is None:
        raise ValueError('Unknown resource')
    RecommendationFeedback.objects.create(resource_id=data.resource_id,helpful=data.helpful)
    return {'saved':True,'comment_stored':False,'message':'Thank you. Only the resource and helpful/not helpful response were saved. Comments are discarded for privacy.'}
