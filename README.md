pyinstaller --onefile -i='ico.ico' --hide-console=hide-early --add-binary "ffmpeg.exe;."   --add-data "loading.gif;." --add-data "overlay.gif;."  youtube_to_mp3.py

git tag v.2.1
git push -u origin && git push --tags
