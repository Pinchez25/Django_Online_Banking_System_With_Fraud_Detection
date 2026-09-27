from django.core.management.base import BaseCommand



class Command(BaseCommand):
    help = "Clear the cached fraud model bundle in the current process."

    def handle(self, *args, **options):
        _load_bundle.cache_clear()
        self.stdout.write(self.style.SUCCESS("Fraud model cache cleared."))
