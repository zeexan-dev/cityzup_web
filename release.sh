
# Prompt the user to continue
read -p "Do you want to proceed with the release? (y/n) " choice
if [[ $choice != "y" ]]; then
  echo "Release aborted."
  exit 0
fi

# Ask for the version number
read -p "Enter the version number for the tag (e.g., 0.0.1): " version

# Check if the tag already exists
if git rev-parse "v$version" >/dev/null 2>&1; then
  echo "Error: Tag 'v$version' already exists."
  echo "To delete the existing tag, run the following commands:"
  echo "git tag -d v$version"
  echo "git push origin :refs/tags/v$version"
  exit 1
fi

# Add the tag and push it to the origin
git tag "v$version"
git push origin "v$version"

