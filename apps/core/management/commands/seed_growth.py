from django.core.management.base import BaseCommand

from apps.core.models import SiteSettings
from apps.finder.models import Source

TOPICS = 'coding OR programming OR scratch OR python OR animation OR "game design" OR robotics OR STEM OR "graphic design"'

# Parent communities only: children's own communities (e.g. gaming subs) are deliberately left out.
DEFAULT_SOURCES = [
    {"name": "Parenting communities (UK, US, CA, AU)", "kind": Source.Kind.REDDIT,
     "community": "Parenting+UKParenting+ukparents+Mommit+daddit+AskParents+raisingkids+AustralianParents"
                  "+CanadaParenting+Parents",
     "query": TOPICS},
    {"name": "Homeschooling communities", "kind": Source.Kind.REDDIT,
     "community": "homeschool+unschool+homeschooling",
     "query": TOPICS},
    {"name": "Learning-to-code communities (parents asking)", "kind": Source.Kind.REDDIT,
     "community": "learnprogramming+learnpython+AskProgramming+gamedev",
     "query": '"my son" OR "my daughter" OR "my kid" OR "my child" OR "year old"'},
    {"name": "All of Reddit: coding classes for kids", "kind": Source.Kind.REDDIT, "community": "",
     "query": '("coding classes" OR "coding lessons" OR "coding club" OR "animation classes") (kids OR son OR daughter)'},
]


class Command(BaseCommand):
    help = "Create settings and the default parent-community sources (safe to run again)."

    def handle(self, *args, **options):
        SiteSettings.load()
        created = 0
        for spec in DEFAULT_SOURCES:
            _, new = Source.objects.get_or_create(name=spec["name"], defaults=spec)
            created += new
        self.stdout.write(self.style.SUCCESS(f"Settings ready; {created} new source(s), {Source.objects.count()} total."))
