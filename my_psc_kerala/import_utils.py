import io
import pandas as pd
from my_psc_kerala.models import ClassLevel, Subject, Question, StudyNote

def import_data_from_file(file_contents, file_name):
    """
    Imports questions or notes from a CSV or Excel file.
    file_contents: bytes (from request.FILES['file'].read()) or file-like object.
    file_name: string representing name of file to determine extension.
    Returns: dict with 'success' (bool), 'imported_count' (int), and 'errors' (list).
    """
    imported_count = 0
    errors = []
    
    try:
        # Load into pandas dataframe
        if file_name.endswith('.csv'):
            # Convert bytes to file-like string stream if needed
            if isinstance(file_contents, bytes):
                stream = io.StringIO(file_contents.decode('utf-8', errors='ignore'))
            else:
                stream = file_contents
            df = pd.read_csv(stream)
        elif file_name.endswith(('.xls', '.xlsx')):
            if isinstance(file_contents, bytes):
                stream = io.BytesIO(file_contents)
            else:
                stream = file_contents
            df = pd.read_excel(stream)
        else:
            return {"success": False, "imported_count": 0, "errors": ["Unsupported file format. Please upload CSV or Excel."]}
            
        # Standardize columns to lowercase for flexible matching
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Check type of import
        if 'question_text' in df.columns:
            # Question Import
            required_cols = ['class_name', 'subject_name', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                return {"success": False, "imported_count": 0, "errors": [f"Missing required columns: {', '.join(missing)}"]}
                
            for index, row in df.iterrows():
                try:
                    class_name = str(row['class_name']).strip()
                    subject_name = str(row['subject_name']).strip()
                    q_text = str(row['question_text']).strip()
                    opt_a = str(row['option_a']).strip()
                    opt_b = str(row['option_b']).strip()
                    opt_c = str(row['option_c']).strip()
                    opt_d = str(row['option_d']).strip()
                    correct = str(row['correct_answer']).strip().upper()
                    explanation = str(row.get('explanation', '')).strip()
                    
                    if correct not in ['A', 'B', 'C', 'D']:
                        errors.append(f"Row {index+2}: Correct answer must be A, B, C, or D (got '{correct}')")
                        continue
                        
                    # Create hierarchies
                    class_level, _ = ClassLevel.objects.get_or_create(name=class_name)
                    subject, _ = Subject.objects.get_or_create(class_level=class_level, name=subject_name)
                    
                    # Create question
                    Question.objects.create(
                        subject=subject,
                        question_text=q_text,
                        option_a=opt_a,
                        option_b=opt_b,
                        option_c=opt_c,
                        option_d=opt_d,
                        correct_answer=correct,
                        explanation=explanation
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Row {index+2}: Error saving question - {str(e)}")
                    
        elif 'content' in df.columns and 'title' in df.columns:
            # Study Note Import
            required_cols = ['class_name', 'subject_name', 'title', 'content']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                return {"success": False, "imported_count": 0, "errors": [f"Missing required columns: {', '.join(missing)}"]}
                
            for index, row in df.iterrows():
                try:
                    class_name = str(row['class_name']).strip()
                    subject_name = str(row['subject_name']).strip()
                    title = str(row['title']).strip()
                    content = str(row['content']).strip()
                    
                    # Create hierarchies
                    class_level, _ = ClassLevel.objects.get_or_create(name=class_name)
                    subject, _ = Subject.objects.get_or_create(class_level=class_level, name=subject_name)
                    
                    # Create study note
                    StudyNote.objects.create(
                        class_level=class_level,
                        subject=subject,
                        title=title,
                        content=content
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Row {index+2}: Error saving study note - {str(e)}")
        else:
            return {
                "success": False, 
                "imported_count": 0, 
                "errors": ["Columns not recognized. For questions, include 'question_text'. For notes, include 'title' and 'content'."]
            }
            
        return {
            "success": len(errors) == 0 or imported_count > 0,
            "imported_count": imported_count,
            "errors": errors
        }
    except Exception as e:
        return {"success": False, "imported_count": 0, "errors": [f"File parsing error: {str(e)}"]}
