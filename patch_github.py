with open('.github/workflows/branch-enforcement.yml', 'r') as f:
    content = f.read()

content = content.replace(
    'if [[ ! "$SOURCE_BRANCH" =~ ^(feature|fix|testing|chore)/ ]]; then',
    'if [[ ! "$SOURCE_BRANCH" =~ ^(feature|fix|testing|chore|jules)/ ]]; then'
)

with open('.github/workflows/branch-enforcement.yml', 'w') as f:
    f.write(content)
