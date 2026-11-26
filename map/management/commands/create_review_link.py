from django.core.management.base import BaseCommand, CommandError
from lifeline_core.repository import directory
from map.curation import make_review_token

class Command(BaseCommand):
    help='Create an expiring resource-tag review link. Does not send messages.'
    def add_arguments(self,parser):
        parser.add_argument('resource_id',type=int)
        parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    def handle(self,*args,**options):
        if not directory().get(options['resource_id']): raise CommandError('Unknown resource')
        self.stdout.write(options['base_url'].rstrip('/')+'/review/'+make_review_token(options['resource_id'])+'/')
