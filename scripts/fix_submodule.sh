#!/bin/bash

echo "Removing broken submodule reference..."

# Remove from git index (won't delete the actual folder)
git rm --cached nexa-ai-document-analyzer

# Remove any submodule config
git config --file .git/config --remove-section submodule.nexa-ai-document-analyzer 2> /dev/null

# Remove from .git/modules if exists
rm -rf .git/modules/nexa-ai-document-analyzer

# Add to .gitignore to keep the folder but not track it
echo "nexa-ai-document-analyzer/" >> .gitignore

# Commit the changes
git add .gitignore
git commit -m "Fix: Remove broken submodule reference for nexa-ai-document-analyzer"

echo "Done! The folder remains but is no longer tracked as a submodule."
