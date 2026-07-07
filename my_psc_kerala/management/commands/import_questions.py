import os
from django.core.management.base import BaseCommand, CommandError
from my_psc_kerala.import_utils import import_data_from_file

class Command(BaseCommand):
    help = 'Bulk imports questions or study notes from a CSV or Excel file.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the CSV or Excel file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        if not os.path.exists(file_path):
            raise CommandError(f"File '{file_path}' does not exist.")

        self.stdout.write(self.style.NOTICE(f"Importing data from '{file_path}'..."))
        
        try:
            with open(file_path, 'rb') as f:
                file_contents = f.read()
            file_name = os.path.basename(file_path)
            
            result = import_data_from_file(file_contents, file_name)
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"Successfully imported {result['imported_count']} items!"))
            else:
                self.stdout.write(self.style.WARNING(f"Import finished with issues. {result['imported_count']} items imported."))
                
            if result['errors']:
                self.stdout.write(self.style.ERROR("Errors / Warnings encountered:"))
                for err in result['errors']:
                    self.stdout.write(self.style.ERROR(f"  - {err}"))
                    
        except Exception as e:
            raise CommandError(f"Failed to import data: {str(e)}")
