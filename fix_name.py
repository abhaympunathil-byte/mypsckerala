import glob

for f in glob.glob('templates/*.html'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace('Aspirant Kerala', 'My PSC Kerala')
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
        
print("Replaced successfully")
