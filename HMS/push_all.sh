#!/bin/bash

echo "Adding all changes..."
git add .

echo ""
echo "Enter your commit message:"
read commit_message

git commit -m "$commit_message"

echo ""
echo "Pushing to GitHub..."
git push

echo "Done."
