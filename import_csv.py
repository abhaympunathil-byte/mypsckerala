import os
import sys
import csv
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'psc_project.settings')
django.setup()

from my_psc_kerala.models import ClassLevel, Subject, Question

def import_questions(csv_file_path):
    print(f"Importing questions from {csv_file_path}...")
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # If the file is tab-separated, we need to handle that, but dictreader defaults to comma.
        # Let's check the delimiter by peeking
        csvfile.seek(0)
        first_line = csvfile.readline()
        csvfile.seek(0)
        
        if '\t' in first_line and ',' not in first_line:
            reader = csv.DictReader(csvfile, delimiter='\t')
        
        count = 0
        for row in reader:
            if not row.get('class_name') or not row.get('question_text'):
                continue
                
            class_name = row['class_name'].strip()
            subject_name = row['subject_name'].strip()
            
            # Get or create ClassLevel
            class_level, _ = ClassLevel.objects.get_or_create(name=class_name)
            
            # Get or create Subject
            subject, _ = Subject.objects.get_or_create(class_level=class_level, name=subject_name)
            
            # Create Question
            Question.objects.create(
                subject=subject,
                question_text=row['question_text'].strip(),
                option_a=row['option_a'].strip(),
                option_b=row['option_b'].strip(),
                option_c=row['option_c'].strip(),
                option_d=row['option_d'].strip(),
                correct_answer=row['correct_answer'].strip().upper(),
                explanation=row['explanation'].strip() if row.get('explanation') else ''
            )
            count += 1
            
    print(f"Successfully imported {count} questions.")

if __name__ == '__main__':
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock_data', 'questions_new.csv')
    if os.path.exists(csv_path):
        import_questions(csv_path)
    else:
        print(f"File not found: {csv_path}")
