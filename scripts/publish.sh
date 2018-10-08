git config --global user.name "semantic-release (via TravisCI)"
git config --global user.email "semantic-release@travis"
pip install python-semantic-release
semantic-release publish
